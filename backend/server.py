import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Optional
import json
import uuid
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from context import prompt

# Load environment variables
load_dotenv(override=True)

app = FastAPI()

# Configure CORS
origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

USE_BEDROCK = os.getenv('USE_BEDROCK', 'false').lower() == 'true'
BEDROCK_MODEL_ID = os.getenv(
    'BEDROCK_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')

if USE_BEDROCK:
    print('Using AWS Bedrock for LLM interactions')
    # Initialize Bedrock client
    bedrock_client = boto3.client(
        service_name='bedrock',
        region_name=os.getenv('AWS_REGION', 'eu-central-1'),
    )
else:
    print('Using OpenAI API for LLM interactions')
    # Initialize OpenAI client
    client = OpenAI()

# Memory Storage Configuration
USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
S3_BUCKET = os.getenv('S3_BUCKET', '')

if not USE_S3:
    MEMORY_DIR = Path('../memory')
    MEMORY_DIR.mkdir(exist_ok=True)

# S3 Client Initialization
if USE_S3:
    s3_client = boto3.client('s3')


# Request/Response models

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class Message(BaseModel):
    role: str
    content: str
    timestamp: str

# Memory functions


def get_memory_path(session_id: str) -> str:
    '''Get file path for a given session ID'''
    return f'{session_id}.json'


def load_conversation(session_id: str) -> list[ChatCompletionMessageParam]:
    '''Load conversation history from storage'''
    if USE_S3:
        try:
            # Check if object exists in S3
            s3_client.head_object(
                Bucket=S3_BUCKET, Key=get_memory_path(session_id))

            # If it exists, get the object and read its content
            response = s3_client.get_object(
                Bucket=S3_BUCKET, Key=get_memory_path(session_id))
            result: list[ChatCompletionMessageParam] = json.loads(
                response['Body'].read().decode('utf-8'))
            return result
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return []
            else:
                raise e

    # Local file storage
    file_path = MEMORY_DIR / f'{session_id}.json'
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            result: list[ChatCompletionMessageParam] = json.load(f)
            return result
    return []


def save_conversation(session_id: str, messages: list[ChatCompletionMessageParam|dict]):
    '''Save conversation history to storage'''
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id),
            Body=json.dumps(messages, indent=2,
                            ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        return

    # Local file storage
    file_path = MEMORY_DIR / f'{session_id}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)


def call_bedrock(conversation: list[ChatCompletionMessageParam|dict], user_message: str) -> str:
    """Call AWS Bedrock with conversation history"""

    # Build messages in Bedrock format
    messages = []

    # Add system prompt as first user message
    # Or there's a better way to do this - pass in system=[{"text": prompt()}] to the converse call below
    messages.append({
        "role": "user",
        "content": [{"text": f"System: {prompt()}"}]
    })

    # Add conversation history (limit to last 25 exchanges)
    for msg in conversation[-50:]:
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })

    try:
        # Call Bedrock using the converse API
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=messages,
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0.7,
                "topP": 0.9
            }
        )

        # Extract the response text
        return response["output"]["message"]["content"][0]["text"]

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            # Handle message format issues
            print(f"Bedrock validation error: {e}")
            raise HTTPException(
                status_code=400, detail="Invalid message format for Bedrock")
        elif error_code == 'AccessDeniedException':
            print(f"Bedrock access denied: {e}")
            raise HTTPException(
                status_code=403, detail="Access denied to Bedrock model")
        else:
            print(f"Bedrock error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Bedrock error: {str(e)}")


@app.get('/')
async def root():
    return {
        'message': 'AI Digital Twin API with Memory',
        'memory_enabled': True,
        'storage': 'S3' if USE_S3 else 'local',
        'ai_model': BEDROCK_MODEL_ID if USE_BEDROCK else 'OpenAI GPT-4o-mini'
    }


@app.get('/health')
async def health_check():
    return {
        'status': 'healthy',
        # 'openai_api': 'reachable' if client else 'unreachable',
        'use_s3': USE_S3,
        'use_bedrock': USE_BEDROCK,
        'ai_model': BEDROCK_MODEL_ID if USE_BEDROCK else 'OpenAI GPT-4o-mini'
    }


@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        logging.info(f'Chat request received for session: {session_id}')

        # Load conversation history
        conversation:list[ChatCompletionMessageParam|dict]= load_conversation(session_id)

        # Build messages with history
        messages: list[ChatCompletionMessageParam|dict] = [
            {'role': 'system', 'content': prompt()}]
        logging.info(f'Loaded conversation history for session {session_id}: {conversation}')

        # Add conversation history
        # Limit to last 10 messages for context window
        for msg in conversation[-10:]:
            messages.append(msg)

        # Add current message
        messages.append({'role': 'user', 'content': request.message})

        if USE_BEDROCK:
            logging.info('Calling Bedrock API')
            assistant_response = call_bedrock(conversation, request.message)
            logging.info('Received response from Bedrock')
        else:
            # Call OpenAI API
            logging.info('Calling OpenAI API')
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=messages
            )
            assistant_response = response.choices[0].message.content
            logging.info('Received response from OpenAI API')

        # Update conversation history
        conversation.append({'role': 'user', 'content': request.message})
        conversation.append(
            {'role': 'assistant', 'content': assistant_response})

        # Save updated conversation
        save_conversation(session_id, conversation)

        return ChatResponse(
            response=assistant_response or 'Sorry, I couldn\'t generate a response.',
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/sessions/{session_id}')
async def get_session(session_id: str):
    '''Get conversation history for a specific session'''
    try:
        conversation = load_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail='Session not found')
        return {'session_id': session_id, 'messages': conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/sessions')
async def list_sessions():
    '''List all conversation sessions'''
    sessions = []
    for file_path in MEMORY_DIR.glob('*.json'):
        session_id = file_path.stem
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
            sessions.append({
                'session_id': session_id,
                'message_count': len(conversation),
                'last_message': conversation[-1]['content'] if conversation else None
            })
    return {'sessions': sessions}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
