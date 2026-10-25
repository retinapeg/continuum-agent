"""Strict proposal/capability schemas: provider text is data, never a command."""
from jsonschema import Draft202012Validator, FormatChecker


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
            'additionalProperties': False}


TEXT = {'type': 'string', 'maxLength': 12000}
ID = {'type': 'string', 'maxLength': 100}
IDS = {'type': 'array', 'items': ID, 'maxItems': 30}
CAPABILITIES = {
    'read_document': obj({'path': TEXT}),
    'search_memory': obj({'query': TEXT}),
    'inspect_events': obj({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20}}),
    'update_plan': obj({'goal_id': ID, 'plan': TEXT}),
    'create_artifact': obj({'path': TEXT, 'content': TEXT, 'sources': IDS, 'goal_id': ID}),
    'request_clarification': obj({'question': TEXT, 'topic': ID, 'evidence_ids': IDS}),
    'draft_task': obj({'title': TEXT, 'instructions': TEXT, 'sources': IDS}),
}
ACTION = {'oneOf': [obj({'capability': {'const': name}, 'args': schema}) for name, schema in CAPABILITIES.items()]}
PROPOSAL = obj({
    'summary': {'type': 'string', 'maxLength': 1600},
    'actions': {'type': 'array', 'items': ACTION, 'maxItems': 6},
    'memory_updates': {'type': 'array', 'maxItems': 6, 'items': obj({
        'kind': {'enum': ['fact', 'preference', 'question']}, 'subject': ID, 'content': TEXT,
        'evidence_ids': IDS, 'supersedes': {'type': ['string', 'null']}})},
    'goal_updates': {'type': 'array', 'maxItems': 6, 'items': obj({
        'id': ID, 'status': {'enum': ['queued', 'waiting-for-input', 'succeeded', 'failed']}, 'evidence_ids': IDS})},
    'message': obj({'text': {'type': 'string', 'maxLength': 2000},
                    'reason': {'enum': ['reply', 'new_evidence', 'deadline', 'blocked', 'conflict', 'none']},
                    'topic': ID, 'evidence_ids': IDS}),
    'next_delay': {'type': 'number', 'minimum': 5, 'maximum': 3600},
})


def validate(schema, value):
    import json
    json.dumps(value, allow_nan=False)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def empty_proposal(summary='No relevant change. Waiting.'):
    return {'summary': summary, 'actions': [], 'memory_updates': [], 'goal_updates': [],
            'message': {'text': '', 'reason': 'none', 'topic': 'idle', 'evidence_ids': []}, 'next_delay': 60}
