"""LangChain structured generation shared by the coach, pilot and Chester."""
import base64
from dataclasses import dataclass
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit
import uuid


class AgentCancelled(Exception):
    pass


class InvalidAgentResponse(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    schema: dict
    run: Path
    image: Path | None
    cancel: threading.Event | None
    timeout: float

    def check_cancelled(self):
        if self.cancel and self.cancel.is_set():
            raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')


class StructuredGeneration:
    default_timeout = 180

    def __init__(self, directory, provider):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self.model = provider.model

    def available(self):
        return self.provider.available()

    def generate(self, prompt, schema, *, image=None, cancel=None, timeout=None):
        run = self.directory / uuid.uuid4().hex
        request = GenerationRequest(
            prompt, schema, run, image, cancel, self.default_timeout if timeout is None else timeout,
        )
        request.check_cancelled()
        try:
            from langchain_core.runnables import RunnableLambda
            from jsonschema import validate, ValidationError
        except ImportError as error:
            raise RuntimeError('Installez les dépendances IA avec pip install -r requirements-ai.txt.') from error

        def parse_response(content):
            request.check_cancelled()
            try:
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError('Objet JSON attendu')
                validate(result, schema)
                return result
            except (ValueError, TypeError, ValidationError) as error:
                raise InvalidAgentResponse(str(error)) from error

        run.mkdir()
        (run / 'schema.json').write_text(json.dumps(schema), encoding='utf-8')
        (run / 'prompt.txt').write_text(prompt, encoding='utf-8')
        chain = RunnableLambda(self.provider.invoke) | RunnableLambda(parse_response)
        result = chain.invoke(request)
        request.check_cancelled()
        (run / 'response.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        return result


class LocalModel:
    def __init__(self):
        self.endpoint = urlsplit(os.environ.get('INAZUMIA_LLM_URL', 'http://127.0.0.1:1234/v1'))
        if self.endpoint.scheme != 'http' or self.endpoint.hostname not in ('127.0.0.1', 'localhost', '::1') or self.endpoint.username or self.endpoint.password or self.endpoint.query or self.endpoint.fragment:
            raise ValueError('INAZUMIA_LLM_URL doit être une adresse HTTP locale sans authentification.')
        self.model = os.environ.get('INAZUMIA_LLM_MODEL', 'qwen/qwen3.5-9b')

    def available(self):
        connection = http.client.HTTPConnection(
            self.endpoint.hostname, self.endpoint.port or 80, timeout=1,
        )
        try:
            connection.request('GET', self.endpoint.path.rstrip('/') + '/models')
            response = connection.getresponse()
            return response.status == 200 and any(
                model.get('id') == self.model for model in json.load(response).get('data', [])
            )
        except (OSError, ValueError, AttributeError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    def invoke(self, request):
        from httpx import Client
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI
        from openai import APITimeoutError, ContentFilterFinishReasonError, LengthFinishReasonError

        request.check_cancelled()
        content = [{'type': 'text', 'text': request.prompt}]
        if request.image:
            encoded = base64.b64encode(Path(request.image).read_bytes()).decode('ascii')
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + encoded}})
        response_format = {
            'type': 'json_schema',
            'json_schema': {'name': 'agent_response', 'strict': True, 'schema': request.schema},
        }

        def generate():
            # Ignore proxy settings and redirects so screenshots stay on loopback.
            with Client(trust_env=False) as client:
                model = ChatOpenAI(
                    base_url=self.endpoint.geturl().rstrip('/'), api_key='lm-studio',
                    model=self.model, temperature=0.2, timeout=request.timeout,
                    max_retries=0,
                    # LM Studio documents max_tokens, which ChatOpenAI normally renames.
                    extra_body={'max_tokens': 256 if request.timeout <= 9 else 1500},
                    use_responses_api=False, http_client=client,
                )
                return model.invoke(
                    [HumanMessage(content=content)],
                    response_format=response_format, reasoning_effort='none',
                )

        completed = threading.Event()
        outcome = {}

        def call_model():
            try:
                outcome['response'] = generate()
            except Exception as error:
                outcome['error'] = error
            finally:
                completed.set()

        deadline = time.monotonic() + request.timeout
        threading.Thread(target=call_model, daemon=True).start()
        while not completed.wait(min(0.1, max(0, deadline - time.monotonic()))):
            request.check_cancelled()
            if time.monotonic() >= deadline:
                raise TimeoutError('IA locale trop lente ; émulation laissée en pause.')
        request.check_cancelled()
        if 'error' in outcome:
            error = outcome['error']
            if isinstance(error, APITimeoutError):
                raise TimeoutError('IA locale trop lente ; émulation laissée en pause.') from error
            if isinstance(error, (LengthFinishReasonError, ContentFilterFinishReasonError)):
                raise InvalidAgentResponse('Réponse interrompue ou budget de tokens atteint') from error
            (request.run / 'error.txt').write_text(str(error), encoding='utf-8')
            raise RuntimeError(
                f'Échec de l’IA locale. Démarrez le serveur LM Studio avec le modèle {self.model}. Détail : {error}'
            ) from error
        response = outcome['response']
        (request.run / 'agent.log').write_text(response.model_dump_json(), encoding='utf-8')
        if response.response_metadata.get('finish_reason') != 'stop':
            raise InvalidAgentResponse('Réponse interrompue ou budget de tokens atteint')
        return response.content


class CodexModel:
    model = 'Codex (configuration du CLI)'

    def __init__(self):
        self.executable = shutil.which('codex')

    def invoke(self, request):
        if not self.executable:
            raise RuntimeError('Codex CLI absent. Installez Codex et connectez votre compte pour utiliser les agents.')
        run, image, cancel, timeout = request.run, request.image, request.cancel, request.timeout
        schema_path = run / 'schema.json'
        # Keep the CLI output separate until the shared parser has validated it.
        output_path = run / 'codex-response.json'
        arguments = [self.executable,'exec','--ephemeral','--ignore-user-config',
                     '--skip-git-repo-check','--sandbox','read-only',
                     '--cd',str(run.resolve()),'--output-schema',str(schema_path.resolve()),
                     '--output-last-message',str(output_path.resolve()),'--color','never']
        if image:
            arguments.extend(['--image',str(Path(image).resolve())])
        arguments.append('-')
        with (run/'agent.log').open('w',encoding='utf-8') as log:
            process = subprocess.Popen(arguments,stdin=subprocess.PIPE,stdout=log,stderr=log,
                text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                process.stdin.write(request.prompt)
                process.stdin.close()
                deadline = time.monotonic()+timeout
                while process.poll() is None:
                    if cancel and cancel.wait(.2):
                        raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')
                    if not cancel:
                        time.sleep(.2)
                    if time.monotonic()>deadline:
                        raise TimeoutError('Agent trop lent ; émulation laissée en pause.')
                if process.returncode or not output_path.is_file():
                    raise RuntimeError('Échec de l’agent Codex. Consultez le journal local : '+str(run/'agent.log'))
                return output_path.read_text(encoding='utf-8')
            finally:
                if process.poll() is None:
                    if hasattr(subprocess,'CREATE_NO_WINDOW'):
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW,check=False)
                    else:
                        process.kill()
                    process.wait(timeout=10)

    def available(self):
        return bool(self.executable)
