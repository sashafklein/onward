You are decomposing a chunk into executable tasks.

Output strict JSON with this exact shape:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "acceptance": ["string"],
      "model": "string",
      "human": false
    }
  ]
}

Constraints:
- Return at least one task.
- Each task must include one or more acceptance checks.
- Do not include markdown fences or any non-JSON text.
