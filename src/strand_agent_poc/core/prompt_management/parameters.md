question --> user_prompt
system_prompt --> default planner system user_prompt


## Planner system prompt
```java
DEFAULT_PLANNER_SYSTEM_PROMPT = PLANNER_RESPONSIBILITY + PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT
        + FINAL_RESULT_RESPONSE_INSTRUCTIONS;
```

planner_prompt --> get from input with key `planner_prompt`
planner_prompt_template -->
planner_with_history_template -->

reflect_prompt --> get from input with key `reflect_prompt`
reflect_prompt_template -->

```sh
${parameters.tools_prompt}
${parameters.planner_prompt}

Objective: ```${parameters.user_prompt}```

Original plan:
[${parameters.steps}]

You have currently executed the following steps from the original plan:
[${parameters.completed_steps}]

${parameters.reflect_prompt}

.Remember: Respond only in JSON format following the required schema.
```

plan_execute_reflect_response_format --> PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT
no_escape_params --> tool_configs,_tools

memory_id --> read from input
completed_steps --> read from memory and populate history into complete steps
message_history_limit --> read from input and default is 10
max_steps --> 10

`tools_prompt` --->
```
In this environment, you have access to the tools listed below. Use these tools to create your plan, and do not reference or use any tools not listed here.

Tool 1 - <tool_name>: <toolDescription>
Tool 2 - <tool_name>: <toolDescription>

No other tools are available. Do not invent tools. Only use tools to create the plan.\n\n

```

---step2---
prompt_template --> DEFAULT_PLANNER_PROMPT_TEMPLATE

```java
${parameters.tools_prompt}
${parameters.planner_prompt}
Objective: ${parameters.user_prompt}

Remember: Respond only in JSON format following the required schema.
```


plannerWithHistoryPromptTemplate --> `DEFAULT_PLANNER_WITH_HISTORY_PROMPT_TEMPLATE`

```java
${parameters.tools_prompt}
${parameters.planner_prompt}
Objective: ```${parameters.user_prompt}```

You have currently executed the following steps:
[${parameters.completed_steps}]

Remember: Respond only in JSON format following the required schema.
```

replace all variables and put it into `prompt` filed




executor_system_prompt --> executor system prompt === `EXECUTOR_RESPONSIBILITY`

## Final request body
```json
{
    "system": [
        {
            "text": "${parameters.system_prompt}"
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "${parameters.prompt}"
                }
            ]
        }
    ]
}
```


```
completedSteps.add(String.format("\nStep %d: %s\n", stepsExecuted + 1, stepToExecute));
                    completedSteps.add(String.format("\nStep %d Result: %s\n", stepsExecuted + 1, results.get(STEP_RESULT_FIELD)));
```
