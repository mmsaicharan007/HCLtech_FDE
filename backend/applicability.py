"""Transparent heuristics, not a root-cause classifier or probability model."""
import re

INTEGRATIONS = ('salesforce', 'hubspot', 'okta', 'snowflake', 'bigquery', 'shopify', 'redshift', 'stripe')


def signals(text):
    lower = text.lower()
    return {'integrations': sorted(name for name in INTEGRATIONS if re.search(r'\b' + name + r'\b', lower)),
            'errors': sorted(set(re.findall(r'\b(?:[45]\d{2}|ERR_[A-Z0-9_]+)\b', text, re.I)))}


def assess(matches, text, category, strong, related):
    query = signals(text)
    eligible = []
    for match in matches:
        ticket = match['ticket']
        past = signals(ticket['subject'] + ' ' + ticket['description'])
        differences = []
        if category and category != ticket['category']:
            differences.append('Product area differs; input metadata may be incorrect.')
        integration_mismatch = bool(query['integrations'] and not set(query['integrations']) <= set(past['integrations']))
        error_mismatch = bool(query['errors'] and not set(map(str.lower, query['errors'])) <= set(map(str.lower, past['errors'])))
        if integration_mismatch:
            differences.append('Requested integration is not documented in this historical problem.')
        if error_mismatch:
            differences.append('Requested error signal is absent or different in the historical problem.')
        match['signals'] = past
        match['differences'] = differences
        similarity = match['cosine_similarity']
        match['applicability'] = ('related' if integration_mismatch or error_mismatch else
                                  'useful_candidate' if similarity >= strong else
                                  'related' if similarity >= related else 'weak')
        if match.get('outcome') == 'confirmed_unresolved':
            match['applicability'] = 'related'
            differences.append('Synthetic feedback says this resolution attempt did not fix the issue.')
        if not integration_mismatch and not error_mismatch:
            eligible.append(match)
    useful = any(m['applicability'] == 'useful_candidate' for m in eligible)
    related_found = any(m['cosine_similarity'] >= related for m in eligible)
    assessment = 'useful_cases' if useful else 'related_cases' if related_found else 'no_useful_match'
    # Preserve ordering within bands; useful candidates should lead the list.
    order = {'useful_candidate': 0, 'related': 1, 'weak': 2}
    matches.sort(key=lambda m: order[m['applicability']])
    return assessment, query
