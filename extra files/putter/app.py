# import streamlit as st
# import streamlit.components.v1 as components

# st.set_page_config(page_title="Puter.js in Streamlit", layout="wide")
# st.title("💬 Puter.js in Streamlit (with Tool Calling & Streaming)")

# # Initialize session state
# if "user_prompt" not in st.session_state:
#     st.session_state.user_prompt = ""
# if "run_js" not in st.session_state:
#     st.session_state.run_js = False

# # User input
# prompt = st.text_input("Enter your prompt:", value="What is 123 multiplied by 456?")
# use_streaming = st.checkbox("Enable streaming", value=True)

# # Trigger JS execution
# if st.button("Run with Puter.js"):
#     st.session_state.user_prompt = prompt
#     st.session_state.run_js = True

# # Only render JS if button was clicked
# if st.session_state.run_js:
#     js_code = f"""
#     <div id="output" style="font-family: sans-serif; line-height: 1.6; white-space: pre-wrap;"></div>

#     <script src="https://js.puter.com/v2/"></script>
#     <script>
#         (async () => {{
#             const prompt = {repr(st.session_state.user_prompt)};
#             const useStreaming = {'true' if use_streaming else 'false'};
#             const tools = [{{
#                 type: "function",
#                 function: {{
#                     name: "calculate",
#                     description: "Perform basic math operations",
#                     parameters: {{
#                         type: "object",
#                         properties: {{
#                             operation: {{ type: "string", enum: ["add", "subtract", "multiply", "divide"] }},
#                             a: {{ type: "number" }},
#                             b: {{ type: "number" }}
#                         }},
#                         required: ["operation", "a", "b"]
#                     }}
#                 }}
#             }}];

#             function appendOutput(text) {{
#                 document.getElementById("output").innerHTML += text;
#             }}

#             try {{
#                 if (useStreaming) {{
#                     appendOutput("<b>📡 Streaming response...</b>\\n\\n");
#                     const stream = await puter.ai.chat(prompt, {{ 
#                         model: "gpt-5-nano", 
#                         stream: true, 
#                         tools: tools 
#                     }});

#                     let toolUsed = false;
#                     for await (const part of stream) {{
#                         if (part?.tool_calls) {{
#                             // Tool calling case
#                             toolUsed = true;
#                             const call = part.tool_calls[0];
#                             const args = JSON.parse(call.function.arguments);
#                             let result;
#                             if (args.operation === "multiply") result = args.a * args.b;
#                             else if (args.operation === "add") result = args.a + args.b;
#                             else if (args.operation === "subtract") result = args.a - args.b;
#                             else if (args.operation === "divide") result = args.a / args.b;

#                             appendOutput(`🧮 AI called calculator: ${{args.a}} ${{args.operation}} ${{args.b}} = ${{result}}`);
#                             return;
#                         }}
#                         if (part?.text) {{
#                             appendOutput(part.text);
#                         }}
#                     }}
#                 }} else {{
#                     const response = await puter.ai.chat(prompt, {{ model: "gpt-5-nano", tools: tools }});
#                     if (response.message?.tool_calls) {{
#                         const call = response.message.tool_calls[0];
#                         const args = JSON.parse(call.function.arguments);
#                         let result;
#                         if (args.operation === "multiply") result = args.a * args.b;
#                         else if (args.operation === "add") result = args.a + args.b;
#                         else if (args.operation === "subtract") result = args.a - args.b;
#                         else if (args.operation === "divide") result = args.a / args.b;

#                         appendOutput(`🧮 AI used calculator: ${{args.a}} ${{args.operation}} ${{args.b}} = ${{result}}`);
#                     }} else {{
#                         appendOutput(response);
#                     }}
#                 }}
#             }} catch (e) {{
#                 appendOutput("❌ Error: " + e.message);
#             }}
#         }})();
#     </script>
#     """

#     components.html(js_code, height=400, scrolling=True)

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Puter.js in Streamlit", layout="wide")
st.title("💬 Puter.js in Streamlit (with Tool Calling & Streaming)")

# Initialize session state
if "user_prompt" not in st.session_state:
    st.session_state.user_prompt = ""
if "run_js" not in st.session_state:
    st.session_state.run_js = False

# User input
prompt = st.text_input("Enter your prompt:", value="What is 123 multiplied by 456?")
use_streaming = st.checkbox("Enable streaming", value=True)

# Trigger JS execution
if st.button("Run with Puter.js"):
    st.session_state.user_prompt = prompt
    st.session_state.run_js = True

# Only render JS if button was clicked
if st.session_state.run_js:
    js_code = f"""
    <style>
        #output {{
            font-family: sans-serif;
            line-height: 1.6;
            white-space: pre-wrap;
            background-color: #ffffff; /* Explicit white background */
            color: #000000; /* Explicit black text */
            padding: 15px;
            border-radius: 8px;
            min-height: 300px;
            overflow-y: auto;
        }}
        .streaming-indicator {{
            color: #007bff;
            font-weight: bold;
        }}
    </style>

    <div id="output">
        <span class="streaming-indicator">📡 Streaming response...</span><br><br>
    </div>

    <script src="https://js.puter.com/v2/"></script>
    <script>
        (async () => {{
            const prompt = {repr(st.session_state.user_prompt)};
            const useStreaming = {'true' if use_streaming else 'false'};
            const tools = [{{
                type: "function",
                function: {{
                    name: "calculate",
                    description: "Perform basic math operations",
                    parameters: {{
                        type: "object",
                        properties: {{
                            operation: {{ type: "string", enum: ["add", "subtract", "multiply", "divide"] }},
                            a: {{ type: "number" }},
                            b: {{ type: "number" }}
                        }},
                        required: ["operation", "a", "b"]
                    }}
                }}
            }}];

            function appendOutput(text) {{
                const outputDiv = document.getElementById("output");
                outputDiv.innerHTML += text;
                // Scroll to bottom for streaming
                outputDiv.scrollTop = outputDiv.scrollHeight;
            }}

            try {{
                if (useStreaming) {{
                    // Clear initial indicator
                    document.getElementById("output").innerHTML = '<span class="streaming-indicator">📡 Streaming response...</span><br><br>';
                    
                    const stream = await puter.ai.chat(prompt, {{ 
                        model: "gpt-5-nano", 
                        stream: true, 
                        tools: tools 
                    }});

                    let toolUsed = false;
                    for await (const part of stream) {{
                        if (part?.tool_calls) {{
                            toolUsed = true;
                            const call = part.tool_calls[0];
                            const args = JSON.parse(call.function.arguments);
                            let result;
                            if (args.operation === "multiply") result = args.a * args.b;
                            else if (args.operation === "add") result = args.a + args.b;
                            else if (args.operation === "subtract") result = args.a - args.b;
                            else if (args.operation === "divide") result = args.a / args.b;

                            appendOutput(`<br><br>🧮 AI called calculator: ${{args.a}} ${{args.operation}} ${{args.b}} = ${{result}}`);
                            return;
                        }}
                        if (part?.text) {{
                            appendOutput(part.text);
                        }}
                    }}
                    if (!toolUsed) {{
                        appendOutput('<br><br>✅ Streaming complete.');
                    }}
                }} else {{
                    const response = await puter.ai.chat(prompt, {{ model: "gpt-5-nano", tools: tools }});
                    if (response.message?.tool_calls) {{
                        const call = response.message.tool_calls[0];
                        const args = JSON.parse(call.function.arguments);
                        let result;
                        if (args.operation === "multiply") result = args.a * args.b;
                        else if (args.operation === "add") result = args.a + args.b;
                        else if (args.operation === "subtract") result = args.a - args.b;
                        else if (args.operation === "divide") result = args.a / args.b;

                        appendOutput(`<br><br>🧮 AI used calculator: ${{args.a}} ${{args.operation}} ${{args.b}} = ${{result}}`);
                    }} else {{
                        appendOutput(`<br><br>${{response}}`);
                    }}
                }}
            }} catch (e) {{
                appendOutput('<br><br>❌ Error: ' + e.message);
            }}
        }})();
    </script>
    """

    # ⚠️ CRITICAL: Set a large height for the iframe
    components.html(js_code, height=600, scrolling=True)