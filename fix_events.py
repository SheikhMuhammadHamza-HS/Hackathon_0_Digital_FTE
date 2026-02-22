#!/usr/bin/env python
"""Fix event dataclass field ordering issues."""

import re

# Read the event_bus.py file
with open('ai_employee/core/event_bus.py', 'r') as f:
    content = f.read()

# Pattern to match Event subclasses with non-default fields
pattern = r'@dataclass\nclass (\w+Event)\(Event\):\s*\n\s*"""([^"]*)"""\s*\n((?:.*?:\s*[^=]+.*\n)+)'

def fix_event_class(match):
    class_name = match.group(1)
    docstring = match.group(2)
    fields = match.group(3)

    # Fix each field to have a default factory
    lines = fields.strip().split('\n')
    fixed_lines = []

    for line in lines:
        if ':' in line and '=' not in line and not line.strip().startswith('#'):
            # Field without default
            field_name = line.split(':')[0].strip()
            field_type = line.split(':')[1].strip()

            # Add default factory based on type
            if 'str' in field_type:
                line = f"    {field_name}: {field_type} = field(default_factory='')"
            elif 'float' in field_type or 'int' in field_type:
                line = f"    {field_name}: {field_type} = field(default_factory=0)"
            elif 'bool' in field_type:
                line = f"    {field_name}: {field_type} = field(default_factory=False)"
            elif 'datetime' in field_type:
                line = f"    {field_name}: {field_type} = field(default_factory=datetime.utcnow)"
            else:
                line = f"    {field_name}: {field_type} = field(default_factory=lambda: None)"

        fixed_lines.append(line)

    # Add field import if not present
    if 'from dataclasses import field' not in content:
        content = content.replace(
            'from dataclasses import dataclass',
            'from dataclasses import dataclass, field'
        )

    return f"@dataclass\nclass {class_name}(Event):\n    \"\"\"{docstring}\"\"\"\n" + '\n'.join(fixed_lines)

# Apply the fix
new_content = re.sub(pattern, fix_event_class, content)

# Write back to file
with open('ai_employee/core/event_bus.py', 'w') as f:
    f.write(new_content)

print("Fixed event dataclass field ordering issues")