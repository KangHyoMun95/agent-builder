def build_prompt(global_rule, role, task, context):
    return f"""
# GLOBAL RULES
{global_rule}

# ROLE
{role}

# TASK
{task}

# CONTEXT
{context}

# IMPORTANT
Return ONLY valid JSON. No markdown, no text.
Do NOT wrap with ```json
"""