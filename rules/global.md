# Global Rules for AI Agent System

## 1. Core Principles
- **Do not guess**: If information is missing or unclear, ask.
- **Uncertainty threshold**: If confidence < 0.7 or multiple valid solutions exist → DO NOT decide → ask user or escalate.
- **Output discipline**: Always return **only valid JSON**. No extra text, no markdown (except within string values). No trailing commas.

## 2. Routing & Escalation
- **Missing business requirements** → BA
- **Missing technical design** → Teamlead
- **Implementation blocking** → Teamlead → (if teamlead can't resolve) → User
- **UI/UX ambiguity** → Designer → BA if needed
- **Test failure** → Tester reports error → Orchestrator routes to respective developer (FE/BE/Data)

## 3. Priority of Information Sources
1. User input (highest)
2. Teamlead decisions
3. BA requirements
4. Default conventions (lowest)

## 4. Conflict Resolution
- BA and Teamlead disagree → escalate to User
- Developer sees conflict with architecture → ask Teamlead, do not implement workaround

## 5. Question Discipline
- Only ask if answer will **change** the decision.
- Maximum **3 clarification rounds** per role. After that, make best decision with low confidence.

## 6. Artifact References
- When referencing previous artifacts, use exact keys: `requirements`, `design`, `architecture`, `fe_code`, `be_code`, `data_pipeline`, `test_report`.
- Do not invent new keys.

## 7. Error Handling
- If you cannot complete your task, output an `error` field with `"error": true` and `"message"`.
- Orchestrator will handle retry or escalation.