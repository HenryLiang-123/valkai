import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from dotenv import load_dotenv

from chat.services.session import list_strategies, handle_list_sessions, handle_create_session, handle_session_messages
from chat.services.message import handle_send_message
from chat.services.evals import run_harness, run_tests, run_agent_sdk_harness

load_dotenv()

logger = logging.getLogger(__name__)


@require_GET
def strategies(request):
    return JsonResponse(list_strategies(), safe=False)


@require_GET
def list_sessions(request):
    return JsonResponse(handle_list_sessions(), safe=False)


@csrf_exempt
@require_POST
def create_session(request):
    body = json.loads(request.body)
    strategy = body.get("strategy", "")

    result = handle_create_session(strategy)
    if result is None:
        return JsonResponse({"error": f"Invalid strategy: {strategy}"}, status=400)

    return JsonResponse(result, status=201)


@require_GET
def session_messages(request, session_id):
    return JsonResponse(handle_session_messages(session_id))


@csrf_exempt
@require_POST
def send(request, session_id):
    body = json.loads(request.body)
    user_message = body.get("message", "").strip()

    if not user_message:
        return JsonResponse({"error": "message is required"}, status=400)

    result = handle_send_message(session_id, user_message)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def run_evals(request):
    body = json.loads(request.body)
    eval_type = body.get("type", "")

    if eval_type == "harness":
        strategies = body.get("strategies")
        result = run_harness(strategies)
        return JsonResponse(result)
    elif eval_type == "agent_sdk":
        strategies = body.get("strategies")
        result = run_agent_sdk_harness(strategies)
        return JsonResponse(result)
    elif eval_type == "tests":
        test_path = body.get("test_path", "evals/")
        result = run_tests(test_path)
        return JsonResponse(result)
    else:
        return JsonResponse({"error": f"Invalid eval type: {eval_type}. Use 'harness', 'agent_sdk', or 'tests'."}, status=400)
