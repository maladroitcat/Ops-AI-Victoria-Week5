"""
Week 5: Agent Architecture Starter Template

Build an AI agent that answers TechCorp questions using:
- Gemini 2.5 Pro LLM (free tier via Google AI API)
- SQLite database queries
- Policy document retrieval

Complete the TODO sections marked below.
"""

import json
import sqlite3
from typing import Dict, Any
import logging
import os
from pathlib import Path
import re

try:
    import google.genai as genai
except ModuleNotFoundError:
    genai = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
METRICS_PATH = DATA_DIR / "metrics.json"


# TASK 1: Implement the Tool base class


class Tool:
    """Base class for tools the agent can call."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def execute(self, **kwargs) -> str:
        """Execute the tool.

        Subclasses must override this method.
        """
        raise NotImplementedError


# TASK 2: Implement EmployeeLookupTool


class EmployeeLookupTool(Tool):
    """Look up employee information from SQLite database."""

    def __init__(self, db_path: str):
        super().__init__("employee_lookup", "Find employee information by name or ID")
        candidate_path = Path(db_path)
        if not candidate_path.exists() and not candidate_path.is_absolute():
            candidate_path = BASE_DIR / candidate_path
        self.db_path = candidate_path

    def execute(
        self,
        employee_name: str = None,
        employee_id: str = None,
        user_role: str = "engineer",
    ) -> str:
        """Look up employee by name or ID.

        Query the employees table by ID or partial name and return JSON results.
        Sensitive fields are redacted according to user role.

        Args:
            employee_name: Name to search for (partial match ok)
            employee_id: ID to search for (exact match)

        Returns:
            JSON string with employee info or error message
        """
        print("Calling tool: employee_lookup")
        print(f'User role is ' + user_role + '\n')
        try:
            if not employee_id and not employee_name:
                return "Error: employee_name or employee_id is required"

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if employee_id:
                cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
            else:
                cursor.execute(
                    "SELECT * FROM employees WHERE name LIKE ?",
                    (f"%{employee_name}%",),
                )

            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()

            if not rows:
                return "Employee not found"

            redacted_rows = [
                self._redact_sensitive_fields(row, user_role) for row in rows
            ]
            return json.dumps(redacted_rows, indent=2)
        except Exception as e:
            logger.error(f"Employee lookup error: {e}")
            return f"Error: {str(e)}"

    def _redact_sensitive_fields(self, row: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Redact sensitive employee fields based on role permissions."""
        role = (user_role or "engineer").lower()
        redacted = dict(row)

        field_visibility = {
            "salary": {"executive", "hr", "finance"},
            "ssn": {"hr", "finance"},
            "address": {"hr", "executive"},
            "stock_options": {"executive", "finance"},
        }

        for field, allowed_roles in field_visibility.items():
            if field in redacted and role not in allowed_roles:
                redacted[field] = "REDACTED"

        return redacted


# TASK 3: Implement PolicySearchTool


class PolicySearchTool(Tool):
    """Search policy documents by keyword."""

    def __init__(self):
        super().__init__("policy_search", "Search policy documents by keyword or topic")
        with open(DATA_DIR / "documents.json", encoding="utf-8") as f:
            self.documents = json.load(f)

    def execute(self, query: str, limit: int = 5) -> str:
        """Search policies by keyword.

        Search loaded policy documents and return top-N matching documents.

        Args:
            query: Search term
            limit: Max results to return

        Returns:
            Formatted string with matching documents
        """
        print("Calling tool: policy_search")
        try:
            if not query:
                return "No matching policy documents found"

            query_terms = [
                term for term in re.findall(r"[a-zA-Z0-9_]+", query.lower())
                if len(term) > 2
            ]
            if not query_terms:
                query_terms = [query.lower()]

            matches = []
            for doc in self.documents:
                searchable_text = " ".join(
                    [
                        doc.get("title", ""),
                        doc.get("category", ""),
                        doc.get("content", ""),
                    ]
                ).lower()
                score = sum(searchable_text.count(term) for term in query_terms)
                if score > 0:
                    matches.append((score, doc))

            if not matches:
                return "No matching policy documents found"

            matches.sort(key=lambda item: item[0], reverse=True)
            results = []
            for score, doc in matches[:limit]:
                content = doc.get("content", "").strip()
                results.append(
                    {
                        "id": doc.get("id"),
                        "title": doc.get("title"),
                        "category": doc.get("category"),
                        "sensitivity": doc.get("sensitivity"),
                        "score": score,
                        "snippet": self._build_snippet(content, query_terms),
                    }
                )

            return json.dumps(results, indent=2)
        except Exception as e:
            logger.error(f"Policy search error: {e}")
            return f"Error: {str(e)}"

    def _build_snippet(self, content: str, query_terms: list[str]) -> str:
        """Return a snippet centered on the first matching query term."""
        if not content:
            return ""

        lowered_content = content.lower()
        match_positions = [
            lowered_content.find(term)
            for term in query_terms
            if lowered_content.find(term) != -1
        ]

        if not match_positions:
            return content[:500]

        first_match = min(match_positions)
        start = max(first_match - 250, 0)
        end = min(start + 750, len(content))

        if end - start < 750:
            start = max(end - 750, 0)

        snippet = content[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet


# TASK 4: Implement ExpenseQueryTool


class ExpenseQueryTool(Tool):
    """Query expense policies and approval limits."""

    def __init__(self):
        super().__init__("expense_query", "Query expense approval limits by role")
        with open(DATA_DIR / "policies.json", encoding="utf-8") as f:
            self.policies = json.load(f)

    def execute(self, role: str) -> str:
        """Query expense approval limit for a given role.

        Look up a role in self.policies["expense"]["approval_limits"].

        Args:
            role: Employee role (ic1_ic2, ic3, manager, director, vp)

        Returns:
            String with approval limit for the given role
        """
        print("Calling tool: expense_query")
        try:
            normalized_role = self._normalize_role(role)
            approval_limits = self.policies.get("expense", {}).get(
                "approval_limits", {}
            )
            amount = approval_limits.get(normalized_role)

            if amount is None:
                return f"Role not found: {role}"

            return f"Approval limit for {normalized_role}: ${amount}"
        except Exception as e:
            logger.error(f"Expense query error: {e}")
            return f"Error: {str(e)}"

    def _normalize_role(self, role: str) -> str:
        role_text = (role or "").strip().lower().replace("-", "_").replace(" ", "_")
        role_text = role_text.replace("employee", "").strip("_")

        if "ic3" in role_text:
            return "ic3"
        if "ic1" in role_text or "ic2" in role_text:
            return "ic1_ic2"
        if "vice_president" in role_text or role_text == "vp" or " vp" in role_text:
            return "vp"
        if "director" in role_text:
            return "director"
        if "manager" in role_text:
            return "manager"

        aliases = {
            "ic1": "ic1_ic2",
            "ic2": "ic1_ic2",
            "ic1_ic2": "ic1_ic2",
            "ic1/announced_ic2": "ic1_ic2",
            "individual_contributor": "ic1_ic2",
            "senior": "ic3",
            "senior_ic": "ic3",
            "manager": "manager",
            "director": "director",
            "vp": "vp",
            "vice_president": "vp",
        }
        return aliases.get(role_text, role_text)


# TASK 5: Implement the Agent class


class Agent:
    """AI agent that answers questions using Gemini LLM + tools."""

    def __init__(self, db_path: str, api_key: str = None):
        """Initialize the agent.

        Set up the Gemini client, local tools, access-control data, and metrics.

        Args:
            db_path: Path to SQLite database
            api_key: Google AI API key (or use GOOGLE_API_KEY env var)
        """
        self.db_path = db_path
        self.api_key = api_key or GOOGLE_API_KEY
        self.model_id = GEMINI_MODEL

        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set. Get free key at: "
                "https://aistudio.google.com/app/apikey"
            )
        if genai is None:
            raise ImportError(
                "google-genai is not installed. Run: pip install -r requirements.txt"
            )

        self.client = genai.Client(api_key=self.api_key)

        self.tools = {
            "employee_lookup": EmployeeLookupTool(db_path),
            "policy_search": PolicySearchTool(),
            "expense_query": ExpenseQueryTool(),
        }

        metrics = self._load_metrics()
        self.token_count = metrics["total_tokens"]
        self.total_cost = metrics["total_cost"]
        self.queries_run = metrics["total_queries"]

        with open(DATA_DIR / "access_control.json", encoding="utf-8") as f:
            self.access_control = json.load(f)

    def _build_system_prompt(self, user_role: str) -> str:
        """Build system prompt describing available tools.

        Create a prompt that describes the agent, available tools, routing
        format, and user role context.

        Returns:
            System prompt string
        """
        role = self._normalize_user_role(user_role)
        tool_descriptions = "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self.tools.values()
        )
        role_description = self.access_control.get("roles", {}).get(role, {}).get(
            "description", "Standard employee"
        )

        return f"""
You are a TechCorp business assistant. Your job is to decide which local tool
should answer the user's question.

User role: {role}
Role description: {role_description}

Available tools:
{tool_descriptions}

Tool selection rules:
- Use employee_lookup for questions about a specific employee by name or ID.
- Use policy_search for HR, travel, PTO, remote work, compensation, compliance,
  engineering, sales territory, or company policy questions.
- Use expense_query for approval limit questions by role.
- Use none only when no tool is relevant.

Respond with valid JSON only, with this exact shape:
{{"tool": "employee_lookup|policy_search|expense_query|none", "args": {{}}}}

Argument examples:
- {{"tool": "employee_lookup", "args": {{"employee_name": "Brian Yang"}}}}
- {{"tool": "employee_lookup", "args": {{"employee_id": "1"}}}}
- {{"tool": "policy_search", "args": {{"query": "travel policy", "limit": 5}}}}
- {{"tool": "expense_query", "args": {{"role": "manager"}}}}
""".strip()

    def query(self, user_query: str, user_role: str = "engineer") -> Dict[str, Any]:
        """Answer a question using LLM + tools.

        Run the Gemini routing call, execute the selected local tool, synthesize
        a final grounded answer, and update token/cost metrics.

        Args:
            user_query: The question to answer
            user_role: User's role (for access control in future weeks)

        Returns:
            Dict with keys:
            - "answer": str - the response
            - "tokens_used": int - total tokens
            - "cost": float - cost in dollars
            - "role": str - user role
        """
        logger.info(f"Processing query: {user_query}")

        role = self._normalize_user_role(user_role)
        prompt = self._build_system_prompt(role)
        input_tokens = 0
        output_tokens = 0
        tool_name = "none"
        tool_args = {}
        tool_result = ""

        try:
            routing_contents = f"{prompt}\n\nUser question: {user_query}"
            routing_response = self.client.models.generate_content(
                model=self.model_id,
                contents=routing_contents,
            )
            routing_text = self._response_text(routing_response)
            routing_usage = self._extract_usage(routing_response, routing_contents, routing_text)
            input_tokens += routing_usage["input_tokens"]
            output_tokens += routing_usage["output_tokens"]

            try:
                tool_request = self._parse_tool_request(routing_text)
            except ValueError as e:
                logger.warning(f"Invalid tool routing response: {e}")
                tool_request = {
                    "tool": "policy_search",
                    "args": {"query": user_query, "limit": 5},
                }

            tool_name = tool_request.get("tool", "none")
            tool_args = tool_request.get("args", {}) or {}

            if tool_name not in self.tools and tool_name != "none":
                logger.warning(f"Unknown tool requested: {tool_name}")
                tool_name = "policy_search"
                tool_args = {"query": user_query, "limit": 5}

            if tool_name == "none":
                tool_name = "policy_search"
                tool_args = {"query": user_query, "limit": 5}

            tool_result = self._execute_tool(tool_name, tool_args, role)

            final_prompt = self._build_final_prompt(
                user_query=user_query,
                user_role=role,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
            )
            final_response = self.client.models.generate_content(
                model=self.model_id,
                contents=final_prompt,
            )
            answer = self._response_text(final_response)
            final_usage = self._extract_usage(final_response, final_prompt, answer)
            input_tokens += final_usage["input_tokens"]
            output_tokens += final_usage["output_tokens"]
        except Exception as e:
            logger.error(f"Agent query error: {e}")
            answer = (
                "I could not complete the LLM reasoning step. "
                f"Error: {str(e)}"
            )
            if not tool_result:
                tool_result = self._fallback_tool_search(user_query)
                answer += f"\n\nFallback search result:\n{tool_result}"
            estimated = self._estimate_tokens(prompt + user_query + answer)
            input_tokens += estimated // 2
            output_tokens += estimated - (estimated // 2)

        tokens_used = input_tokens + output_tokens
        cost = self._estimate_query_cost(input_tokens, output_tokens)

        self.token_count += tokens_used
        self.total_cost += cost
        self.queries_run += 1
        self._save_metrics()

        return {
            "answer": answer,
            "tokens_used": tokens_used,
            "cost": cost,
            "role": role,
        }

    def _estimate_query_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on tokens.

        Gemini 2.5 Pro pricing:
        - Input: $0.075 per 1M tokens
        - Output: $0.3 per 1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.3
        return input_cost + output_cost

    def get_metrics(self) -> Dict[str, Any]:
        """Return performance metrics.

        Return dict with:
        - total_queries: number of queries processed
        - total_tokens: cumulative tokens used
        - total_cost: cumulative cost in dollars
        - avg_cost_per_query: average cost per query
        """
        avg_cost = self.total_cost / self.queries_run if self.queries_run else 0.0
        return {
            "total_queries": self.queries_run,
            "total_tokens": self.token_count,
            "total_cost": self.total_cost,
            "avg_cost_per_query": avg_cost,
        }

    def _load_metrics(self) -> Dict[str, Any]:
        default_metrics = {
            "total_queries": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

        if not METRICS_PATH.exists():
            return default_metrics

        try:
            with open(METRICS_PATH, encoding="utf-8") as f:
                saved_metrics = json.load(f)
            return {
                "total_queries": int(saved_metrics.get("total_queries", 0)),
                "total_tokens": int(saved_metrics.get("total_tokens", 0)),
                "total_cost": float(saved_metrics.get("total_cost", 0.0)),
            }
        except Exception as e:
            logger.warning(f"Could not load metrics file: {e}")
            return default_metrics

    def _save_metrics(self) -> None:
        metrics = self.get_metrics()
        try:
            with open(METRICS_PATH, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save metrics file: {e}")

    def _normalize_user_role(self, user_role: str) -> str:
        role = (user_role or "engineer").strip().lower()
        if role not in self.access_control.get("roles", {}):
            return "engineer"
        return role

    def _response_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if text:
            return text.strip()
        return str(response).strip()

    def _parse_tool_request(self, response_text: str) -> Dict[str, Any]:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not json_match:
            raise ValueError(f"Could not parse tool request: {response_text}")

        parsed = json.loads(json_match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Tool request must be a JSON object")
        if "tool" not in parsed:
            raise ValueError("Tool request missing 'tool'")
        if "args" not in parsed:
            parsed["args"] = {}
        return parsed

    def _execute_tool(
        self, tool_name: str, tool_args: Dict[str, Any], user_role: str
    ) -> str:
        tool = self.tools[tool_name]
        if tool_name == "employee_lookup":
            return tool.execute(**tool_args, user_role=user_role)
        return tool.execute(**tool_args)

    def _fallback_tool_search(self, user_query: str) -> str:
        try:
            return self.tools["policy_search"].execute(query=user_query, limit=5)
        except Exception as e:
            return f"Fallback search failed: {str(e)}"

    def _build_final_prompt(
        self,
        user_query: str,
        user_role: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str,
    ) -> str:
        return f"""
You are a TechCorp business assistant. Answer the user using only the tool result
below. If the result does not contain enough information, say what is missing.
Do not invent policy details, employee details, or financial numbers.

User role: {user_role}
User question: {user_query}
Tool used: {tool_name}
Tool arguments: {json.dumps(tool_args)}
Tool result:
{tool_result}
""".strip()

    def _extract_usage(
        self, response: Any, input_text: str, output_text: str
    ) -> Dict[str, int]:
        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", None)
            output_tokens = getattr(usage, "candidates_token_count", None)
            total_tokens = getattr(usage, "total_token_count", None)

            if input_tokens is not None and output_tokens is not None:
                return {
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens),
                }
            if total_tokens is not None:
                estimated_output = self._estimate_tokens(output_text)
                estimated_input = max(int(total_tokens) - estimated_output, 0)
                return {
                    "input_tokens": estimated_input,
                    "output_tokens": estimated_output,
                }

        return {
            "input_tokens": self._estimate_tokens(input_text),
            "output_tokens": self._estimate_tokens(output_text),
        }

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text.split()) * 1.3))


# TASK 6: Test your implementation

if __name__ == "__main__":
    """Run the agent from the command line."""
    import sys

    try:
        agent = Agent("data/techcorp.db")
        print("Agent initialized successfully")
        print("Type 'quit' to exit.\n")

        initial_query = " ".join(sys.argv[1:]).strip()
        if initial_query:
            queries = [initial_query]
        else:
            queries = []

        while True:
            if queries:
                user_query = queries.pop(0)
                print(f"Query: {user_query}")
            else:
                user_query = input("Ask a TechCorp question: ").strip()

            if user_query.lower() in {"quit", "exit"}:
                break
            if not user_query:
                continue

            result = agent.query(user_query)
            print(f"\nAnswer: {result['answer']}")
            print(f"Tokens: {result['tokens_used']}")
            print(f"Cost: ${result['cost']:.6f}")

            metrics = agent.get_metrics()
            print(f"Metrics: {metrics}\n")

    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Error running agent")
        sys.exit(1)
