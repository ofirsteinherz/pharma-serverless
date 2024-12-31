import os
import json
import boto3
from typing import Dict, List
from dataclasses import dataclass, field
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pinecone import Pinecone
from litellm import embedding, completion

# Initialize AWS services
ssm = boto3.client('ssm')

@dataclass
class UsageStats:
    """Class for tracking API usage statistics"""
    total_tokens: int = 0
    total_cost: float = 0
    calls: List[Dict] = field(default_factory=list)

class ResponseExtractor:
    """Class for handling LiteLLM response extraction"""
    @staticmethod
    def extract_completion_info(response):
        response_text = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        
        cost = getattr(response, '_private_', {}).get('_hidden_params', {}).get('response_cost', 0.0)
        if cost == 0.0:
            cost = getattr(response, '__pydantic_private__', {}).get('_hidden_params', {}).get('response_cost', 0.0)
        
        return response_text, total_tokens, cost

class UsageTracker:
    """Class for tracking API usage"""
    def __init__(self):
        self.usage_stats = UsageStats()
        self.lock = threading.Lock()
    
    def track(self, tokens, cost):
        with self.lock:
            self.usage_stats.total_tokens += tokens
            self.usage_stats.total_cost += cost
            self.usage_stats.calls.append({
                'tokens': tokens,
                'cost': cost
            })
    
    def get_stats(self):
        return self.usage_stats

class EmbeddingService:
    """Class for handling embeddings"""
    def __init__(self, api_key):
        self.api_key = api_key
        os.environ['OPENAI_API_KEY'] = api_key
    
    def get_embedding(self, text):
        response = embedding(
            model='text-embedding-3-small',
            input=[text]
        )
        return response['data'][0]['embedding']

class PineconeService:
    """Class for handling Pinecone operations"""
    def __init__(self, api_key, index_name):
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
    
    def search(self, query_emb, top_k=25):
        results = self.index.query(
            vector=query_emb,
            top_k=top_k,
            include_metadata=True
        )
        
        documents = [match['metadata']['text'] for match in results['matches']]
        metadatas = [
            {k: v for k, v in match['metadata'].items() if k != 'text'}
            for match in results['matches']
        ]
        
        return documents, metadatas

class QuestionGenerator:
    """Class for generating questions"""
    def __init__(self, usage_tracker, api_key):
        self.usage_tracker = usage_tracker
        self.extractor = ResponseExtractor()
        os.environ['OPENAI_API_KEY'] = api_key
    
    def generate(self, context, disease_name, num_questions=20):
        prompt = f"""Generate {num_questions} key questions about {disease_name} based on the context.
        If the amount of questions in the context is less then {num_questions}, do not make more.
        Make sure the questions are based on the context.
        Each question should have multiple possible answers in the text.
        Return only numbered questions, one per line.
        MAKE SURE THE QUESTIONS ARE ABOUT {disease_name} ONLY AND DONT PROVIDE QUESTIONS THAT NOT RELAVANT TO {disease_name}"""
        
        response = completion(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"{prompt}\n\nContext: {context}"}],
            temperature=0.7
        )
        content, tokens, cost = self.extractor.extract_completion_info(response)
        self.usage_tracker.track(tokens, cost)
        return content.split('\n')

class AnswerVerifier:
    """Class for verifying answers"""
    def __init__(self, usage_tracker, api_key):
        self.usage_tracker = usage_tracker
        self.extractor = ResponseExtractor()
        os.environ['OPENAI_API_KEY'] = api_key
    
    def verify(self, question, context):
        prompt = """Based on the context, extract:
1. All possible answer choices mentioned (as bullets)
2. The correct answer
3. The exact quote supporting the correct answer
4. Any referenced page/section numbers

Format exactly as:
ANSWERS:
* [answer choice 1]
* [answer choice 2]
etc.

CORRECT: [correct answer]
QUOTE: [exact quote]
REFERENCE: [page/section number]

You must make sure the answers make sense based in the question"""
        
        try:
            response = completion(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": f"Context: {context}\nQuestion: {question}\n{prompt}"}
                ],
                temperature=0
            )
            content, tokens, cost = self.extractor.extract_completion_info(response)
            self.usage_tracker.track(tokens, cost)
            return {
                'question': question.strip(),
                'verification': content
            }
        except Exception as e:
            return {
                'question': question.strip(),
                'verification': f"Error occurred during processing: {str(e)}"
            }

class DiseaseAnalyzer:
    """Main class for disease analysis"""
    def __init__(self, openai_api_key, pinecone_api_key, pinecone_index_name):
        self.usage_tracker = UsageTracker()
        self.embedding_service = EmbeddingService(openai_api_key)
        self.pinecone_service = PineconeService(pinecone_api_key, pinecone_index_name)
        self.question_generator = QuestionGenerator(self.usage_tracker, openai_api_key)
        self.answer_verifier = AnswerVerifier(self.usage_tracker, openai_api_key)
        self.completed_questions = set()
        self.lock = threading.Lock()
    
    def process_question(self, args):
        question_num, question, context = args
        result = self.answer_verifier.verify(question, context)
        with self.lock:
            self.completed_questions.add(question_num)
        return result
    
    def analyze_disease(self, disease_name, num_questions=20, max_workers=5):
        query_emb = self.embedding_service.get_embedding(disease_name)
        contexts, metadata = self.pinecone_service.search(query_emb)
        full_context = " ".join(contexts)
        
        questions = self.question_generator.generate(full_context, disease_name, num_questions)
        
        self.total_questions = len(questions)
        self.completed_questions = set()
        
        args = [(i+1, q.strip(), full_context) for i, q in enumerate(questions)]
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_question = {
                executor.submit(self.process_question, arg): arg
                for arg in args
            }
            
            for future in as_completed(future_to_question):
                result = future.result()
                results.append(result)
        
        results.sort(key=lambda x: int(x['question'].split('.')[0]) if x['question'].split('.')[0].isdigit() else 0)
        
        stats = self.usage_tracker.get_stats()
        
        return {
            'disease': disease_name,
            'contexts': contexts,
            'qa_pairs': results,
            'usage_stats': {
                'total_tokens': stats.total_tokens,
                'total_cost': stats.total_cost
            }
        }

def get_secret(secret_name):
    """Retrieve secret from AWS Parameter Store"""
    try:
        response = ssm.get_parameter(
            Name=secret_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")

def handler(event, context):
    """AWS Lambda handler function"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': True,
    }
    
    try:
        # Parse input
        body = json.loads(event.get('body', '{}'))
        disease_name = body.get('disease_name')
        num_questions = min(body.get('num_questions', 20), 50)
        max_workers = min(body.get('max_workers', 5), 10)
        
        if not disease_name:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'disease_name is required'
                })
            }
        
        # Get API keys from environment variables
        openai_api_key = os.environ['OPENAI_API_KEY']
        pinecone_api_key = os.environ['PINECONE_API_KEY']
        pinecone_index_name = os.environ['PINECONE_INDEX_NAME']
        
        # Initialize analyzer
        analyzer = DiseaseAnalyzer(
            openai_api_key=openai_api_key,
            pinecone_api_key=pinecone_api_key,
            pinecone_index_name=pinecone_index_name
        )
        
        # Analyze disease
        results = analyzer.analyze_disease(
            disease_name=disease_name,
            num_questions=num_questions,
            max_workers=max_workers
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(results)
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }