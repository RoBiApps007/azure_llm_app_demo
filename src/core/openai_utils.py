'''
Utility functions to retrieve available models, actual consumption, organization owner, etc. from OpenAI API. 
'''
from openai import OpenAI


def get_list_of_models(
        openai_api_key: str,
        required_substrings: list[str] = None,
        including_substrings: list[str] = None,
        excluded_substrings: list[str] | None = None
    ) -> list[str]:
    '''Retrieve the list of available models from OpenAI API.'''
    if required_substrings is None:
        required_substrings = ['gpt']
    if including_substrings is None:
        including_substrings = ['mini', 'nano']
    if excluded_substrings is None:
        excluded_substrings = ['video', 'audio', 'image', 'transcribe', 'preview', 'tts', 'realtime', 'codex']
    client = OpenAI(api_key=openai_api_key)
    models = client.models.list()

    if not models.data:
        return []

    model_ids = [
        model.id for model in models.data
        if all(sub in model.id for sub in required_substrings) and \
           any(sub in model.id for sub in including_substrings) and \
           not any(sub in model.id for sub in excluded_substrings)
    ]
    return model_ids

def get_organization_owner(openai_api_key: str) -> str:
    '''Retrieve the organization owner from OpenAI API.'''
    client = OpenAI(api_key=openai_api_key)
    orgs = client.organizations.list()
    if orgs.data:
        # Assuming the first organization is the relevant one.
        # The 'owner' field is not directly available in the v1.x Organization object.
        # You might need to adjust this based on what information you need.
        # For now, returning the organization name.
        return orgs.data[0].name
    return "Unknown"

def get_openai_usage(openai_api_key: str, start_date: str, end_date: str) -> dict:
    '''Retrieve the OpenAI API usage between start_date and end_date.'''
    # The Usage API is not available in the v1.x library in the same way.
    # You would typically check usage on the OpenAI dashboard.
    # This function may need to be removed or re-implemented if there's a new way to get usage data.
    # For now, it will raise a NotImplementedError.
    raise NotImplementedError("Usage API not available in openai v1.x library in this manner.")

def get_openai_billing(openai_api_key: str) -> dict:
    '''Retrieve the OpenAI billing information.'''
    # The Billing API is not directly exposed in the v1.x client.
    # This information is usually retrieved from the OpenAI dashboard.
    # This function will raise a NotImplementedError.
    raise NotImplementedError("Billing API not available in openai v1.x library.")

def get_openai_subscription(openai_api_key: str) -> dict:
    '''Retrieve the OpenAI subscription information.'''
    # The Subscription API is not directly exposed in the v1.x client.
    # This information is usually retrieved from the OpenAI dashboard.
    # This function will raise a NotImplementedError.
    raise NotImplementedError("Subscription API not available in openai v1.x library.")


