import asyncio
import base64
import json
import traceback
import nest_asyncio
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit as st
import time
# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

openai_api_key = st.secrets["api_keys"]["openai_api_key"]
proxy_api_key = st.secrets["api_keys"]["proxy_api_key"]

try:
    client = OpenAI(api_key=openai_api_key)
    print("OpenAI client initialized successfully.")
except Exception as e:
    print("Error initializing OpenAI client:", str(e))
    traceback.print_exc()
    client = None

# Global thread initialization (use Streamlit session state to store)
if 'user_thread' not in st.session_state:
    try:
        st.session_state.user_thread = client.beta.threads.create()
        print(f"Created new user thread with ID: {st.session_state.user_thread.id}")
    except Exception as e:
        print("Error creating user thread:", str(e))
        traceback.print_exc()
        st.session_state.user_thread = None

# Proxy setup
PROXY_URL = 'https://proxy.scrapeops.io/v1/'
API_KEY = proxy_api_key

def scrape_content(url):
    """
    Fetches HTML from the target URL using the proxy service, extracts text content,
    and deduplicates href links.
    """
    params = {
        'api_key': API_KEY,
        'url': url,
        'render_js': 'false',
        'residential': 'true',
    }
    
    try:
        with st.spinner(f"Scraping content from {url}..."):
            # Make the request to the proxy service
            response = requests.get(PROXY_URL, params=params, timeout=30)
            response.encoding = 'utf-8'  # Enforce UTF-8 encoding
            
            # Check if the request was successful
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract and clean the text content
                content = soup.get_text(separator="\n", strip=True)
                
                # Extract and deduplicate href links using set comprehension
                links = sorted({a.get('href') for a in soup.find_all('a', href=True) if a.get('href')})
                
                st.success(f"Successfully scraped content from {url}")
                return {
                    'content': content,
                    'links': links  # Return the sorted list of links
                }
            else:
                st.error(f"Failed to fetch the page: {url}, status code: {response.status_code}")
                return None
    except requests.exceptions.Timeout:
        st.error(f"Request timed out while trying to scrape {url}.")
        return None
    except requests.exceptions.TooManyRedirects:
        st.error(f"Too many redirects while trying to scrape {url}.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while scraping {url}: {e}")
        return None
    except Exception as ex:
        st.error(f"Unexpected error while scraping {url}: {ex}")
        traceback.print_exc()
        return None

# Define function specifications for content scraping
tools = [
    {
        "type": "function",
        "function": {
            "name": "scrape_content",
            "description": "Use this function to scrape text content from any URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape content from."
                    }
                },
                "required": ["url"]
            }
        }
    },
    # The following tool definitions are placeholders, adapt as needed
    {"type": "code_interpreter"},
    {"type": "file_search"}
]

# Mapping function names to actual Python callables
available_functions = {
    "scrape_content": scrape_content,
}

# English instructions
english_instructions = """ You are a Company Information Assistant specializing in answering user queries about TREUHAND|SUISSE Zurich Section based on uploaded knowledge files and legal documents.
You have access to internal documents and a custom web scraping function for additional information when needed. Here’s how you should operate:

Key Functions:

Document Search and Analysis: Search through uploaded knowledge files and documents for relevant sections before offering any external sources.
Ensure that responses strictly reference the contents of the uploaded files and are tailored to TREUHAND|SUISSE Zurich Section.

Scraping Feature: If no sufficient information is found internally, use the custom web scraping function to retrieve relevant data without asking for user approval.

Company-Specific Research and Contextual Explanation: Provide detailed answers about TREUHAND|SUISSE Zurich Section’s operations, policies, financials, events, training programs, and membership benefits based on the uploaded documents.

Structured and Clear Responses: Offer structured and clear answers, referencing specific sections of the documents for transparency.

Interaction Flow:

Document First Approach: Always begin by searching through the uploaded documents about TREUHAND|SUISSE Zurich Section. If the information is found, respond by quoting the specific sections.

Web Scraping by Default: If relevant information is not found within the documents, automatically use the custom web scraping function to obtain additional data.

User Query Follow-Up: Ensure that the user has all relevant company-specific information and ask if further clarification or related details are needed.

Clarification and Refinement: Continuously refine your responses based on feedback from the user to provide tailored, accurate information.

Always base your answer on the knowledge uploaded without telling the user that there is a knowledge document.
"""

# German instructions
german_instructions = """ Sie sind ein Unternehmensinformations-Assistent, der sich auf die Beantwortung von Benutzeranfragen zur TREUHAND|SUISSE Sektion Zürich auf Grundlage hochgeladener Wissensdateien und Rechtsdokumente spezialisiert hat.
Sie haben Zugriff auf interne Dokumente und eine benutzerdefinierte Web-Scraping-Funktion, um bei Bedarf zusätzliche Informationen zu erhalten. Hier ist Ihr Vorgehen:

Wichtige Funktionen:

Dokumentensuche und -analyse: Durchsuchen Sie die hochgeladenen Wissensdateien und Dokumente nach relevanten Abschnitten, bevor Sie externe Quellen anbieten.
Stellen Sie sicher, dass Ihre Antworten sich ausschließlich auf die Inhalte der hochgeladenen Dateien beziehen und an TREUHAND|SUISSE Sektion Zürich angepasst sind.

Scraping-Funktion: Wenn in den internen Dokumenten nicht genügend Informationen gefunden werden, nutzen Sie die benutzerdefinierte Web-Scraping-Funktion, ohne die Zustimmung des Benutzers einzuholen.

Unternehmensspezifische Recherche und kontextbezogene Erklärung: Geben Sie detaillierte Antworten zu den Geschäftstätigkeiten, Richtlinien, Finanzen, Veranstaltungen, Schulungsprogrammen und Mitgliedschaftsvorteilen von TREUHAND|SUISSE Sektion Zürich, basierend auf den hochgeladenen Dokumenten.

Strukturierte und klare Antworten: Bieten Sie strukturierte und klare Antworten und verweisen Sie transparent auf spezifische Abschnitte der Dokumente.

Ablauf der Interaktion:

Zuerst Dokumente verwenden: Beginnen Sie immer mit der Recherche in den hochgeladenen Dokumenten über TREUHAND|SUISSE Sektion Zürich. Wenn die Informationen darin gefunden werden, nennen Sie die entsprechenden Abschnitte.

Automatisches Web-Scraping: Wenn in den Dokumenten nicht genügend relevante Informationen vorhanden sind, nutzen Sie automatisch die Web-Scraping-Funktion, um zusätzliche Daten zu erhalten.

Rückfragen zu Benutzeranliegen: Stellen Sie sicher, dass dem Benutzer alle wichtigen Informationen zum Unternehmen vorliegen, und fragen Sie, ob weitere Erläuterungen oder verwandte Details benötigt werden.

Klärung und Verfeinerung: Verfeinern Sie Ihre Antworten kontinuierlich basierend auf dem Feedback des Benutzers, um passgenaue und korrekte Informationen bereitzustellen.

Verfassen Sie Ihre Antworten stets auf Grundlage der hochgeladenen Informationen, ohne den Benutzer darauf hinzuweisen, dass Wissensdokumente verwendet werden.

WICHTIG: Bitte sprechen Sie NUR auf Deutsch.
"""

def create_assistant(file_ids, instructions):
    """
    Creates a new AI assistant with the specified instructions and returns its ID.
    """
    try:
        print(f"Creating assistant with the following instructions:\n{instructions}")
        assistant = client.beta.assistants.create(
            name="Q&A AI assistant",
            instructions=instructions,
            model="gpt-4o-mini",
            tools=tools,
            tool_resources={
                'file_search': {
                    'vector_stores': [{
                        'file_ids': file_ids
                    }]
                }
            }
        )
        print(f"Assistant created with ID: {assistant.id}")
        return assistant.id
    except Exception as e:
        print("Error creating assistant:", str(e))
        traceback.print_exc()
        return None

def safe_tool_call(func, tool_name, **kwargs):
    """
    Safely execute a tool call and handle exceptions.
    """
    try:
        print(f"Calling tool '{tool_name}' with arguments: {kwargs}")
        result = func(**kwargs)
        if result is not None:
            print(f"Tool '{tool_name}' returned: {result}")
            return result
        else:
            print(f"Tool '{tool_name}' returned no content.")
            return f"No content returned from {tool_name}"
    except Exception as e:
        st.error(f"Error in {tool_name}: {str(e)}")
        print(f"Error in tool '{tool_name}': {str(e)}")
        traceback.print_exc()
        return f"Error occurred in {tool_name}: {str(e)}"

def handle_tool_outputs(run):
    """
    Function to handle tool outputs (scrape_content, code_interpreter, etc.).
    """
    tool_outputs = []
    try:
        print("Handling required tool calls...")
        for call in run.required_action.submit_tool_outputs.tool_calls:
            function_name = call.function.name
            function = available_functions.get(function_name)
            
            if not function:
                raise ValueError(f"Function {function_name} not found in available_functions.")
            
            arguments = json.loads(call.function.arguments)
            
            with st.spinner(f"Executing a detailed search..."):
                output = safe_tool_call(function, function_name, **arguments)

            tool_outputs.append({
                "tool_call_id": call.id,
                "output": json.dumps(output)
            })

        print("Submitting tool outputs back to the thread...")
        # Submit the tool outputs
        submitted_result = client.beta.threads.runs.submit_tool_outputs(
            thread_id=st.session_state.user_thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
        print("Tool outputs submitted. Run status:", submitted_result.status)
        return submitted_result

    except Exception as e:
        st.error(f"Error in handle_tool_outputs: {str(e)}")
        print("Error in handle_tool_outputs:", str(e))
        traceback.print_exc()
        return None

async def get_agent_response(assistant_id, user_message):
    """
    Send the user's message to the assistant and await a response with improved error handling.
    """
    try:
        with st.spinner("Processing your request..."):
            print(f"Sending user message to the thread: {user_message}")
            if not st.session_state.user_thread:
                raise ValueError("No user thread found. Please ensure thread creation was successful.")
            
            # Create a new user message in the thread
            client.beta.threads.messages.create(
                thread_id=st.session_state.user_thread.id,
                role="user",
                content=user_message,
            )
            print("User message created in the thread.")

            # Create a new run with the specified assistant ID
            print(f"Creating run with assistant_id={assistant_id}...")
            run = client.beta.threads.runs.create(
                thread_id=st.session_state.user_thread.id,
                assistant_id=assistant_id,
            )
            print(f"Run created. Initial status: {run.status}")

            # Add timeout mechanism
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            
            # Poll the run status with timeout and error handling
            while run.status in ["queued", "in_progress"]:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Run timed out after 5 minutes")
                
                print(f"Current run status: {run.status}. Waiting 1 second...")
                await asyncio.sleep(1)
                
                try:
                    run = client.beta.threads.runs.retrieve(
                        thread_id=st.session_state.user_thread.id,
                        run_id=run.id
                    )
                    print(f"Run status after retrieve: {run.status}")

                    # Check for failed status
                    if run.status == "failed":
                        error_message = f"Run failed with error: {run.last_error.code} - {run.last_error.message}"
                        print(error_message)
                        return error_message, [], []

                    if run.status == "requires_action":
                        print("Run requires action (tool calls). Handling tool outputs...")
                        run = handle_tool_outputs(run)
                        if not run:
                            error_message = "Tool handling failed"
                            print(error_message)
                            return error_message, [], []
                            
                except Exception as e:
                    error_message = f"Error retrieving run status: {str(e)}"
                    print(error_message)
                    return error_message, [], []

            # After run completes, check final status
            if run.status != "completed":
                error_message = f"Run ended with unexpected status: {run.status}"
                if hasattr(run, 'last_error'):
                    error_message += f" (Error: {run.last_error.code} - {run.last_error.message})"
                print(error_message)
                return error_message, [], []

            # Retrieve the messages
            try:
                messages = client.beta.threads.messages.list(
                    thread_id=st.session_state.user_thread.id,
                    limit=1
                )
                if not messages.data:
                    error_message = "No messages found in thread after completion"
                    print(error_message)
                    return error_message, [], []
                
                last_message = messages.data[0]
                
                # Process assistant response
                if last_message.role == "assistant":
                    formatted_response_text = ""
                    download_links = []
                    images = []
                    
                    for content in last_message.content:
                        if content.type == "text":
                            formatted_response_text += content.text.value
                            # Process annotations
                            if hasattr(content.text, 'annotations'):
                                for annotation in content.text.annotations:
                                    if annotation.type == "file_path":
                                        try:
                                            file_id = annotation.file_path.file_id
                                            file_name = annotation.text.split('/')[-1]
                                            file_content = client.files.content(file_id).read()
                                            download_links.append((file_name, file_content))
                                        except Exception as fe:
                                            print(f"Error processing file annotation: {str(fe)}")
                                            
                        elif content.type == "image_file":
                            try:
                                file_id = content.image_file.file_id
                                image_data = client.files.content(file_id).read()
                                images.append((f"{file_id}.png", image_data))
                                formatted_response_text += f"[Image generated: {file_id}.png]\n"
                            except Exception as ie:
                                print(f"Error processing image: {str(ie)}")
                                
                    return formatted_response_text, download_links, images
                else:
                    error_message = f"Unexpected message role: {last_message.role}"
                    print(error_message)
                    return error_message, [], []
                    
            except Exception as e:
                error_message = f"Error retrieving messages: {str(e)}"
                print(error_message)
                return error_message, [], []

    except Exception as e:
        error_message = f"Error in get_agent_response: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return error_message, [], []

def main():
    """
    Main entry point for the Streamlit app.
    """
    st.title("Q&A AI assistant")
    print("Streamlit app started.")

    # Choose language
    st.sidebar.title("Language Selection")
    language_choice = st.sidebar.radio("Please choose a language:", ["English", "German"])
    print(f"Language choice: {language_choice}")

    # Sidebar for assistant selection
    st.sidebar.title("Assistant Configuration")
    assistant_choice = st.sidebar.radio("Choose an option:", ["Create New Assistant", "Use Existing Assistant"])
    
    if language_choice == "German":
        st.sidebar.subheader("Upload German documents")
        current_instructions = german_instructions
    else:
        st.sidebar.subheader("Upload files")
        current_instructions = english_instructions

    # Create new or use existing assistant
    if assistant_choice == "Create New Assistant":
        uploaded_files = st.sidebar.file_uploader(
            "You can upload multiple files here", accept_multiple_files=True
        )
        file_ids = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    file_info = client.files.create(file=uploaded_file, purpose='assistants')
                    print(f"Uploaded file '{uploaded_file.name}' -> assigned file ID: {file_info.id}")
                    file_ids.append(file_info.id)
                except Exception as e:
                    print(f"Error uploading file '{uploaded_file.name}':", str(e))
                    traceback.print_exc()

        if file_ids:
            if st.sidebar.button("Create New Assistant"):
                new_assistant_id = create_assistant(file_ids, current_instructions)
                if new_assistant_id:
                    st.session_state.assistant_id = new_assistant_id
                    st.sidebar.success(f"New assistant created with ID: {st.session_state.assistant_id}")
                else:
                    st.sidebar.error("Failed to create a new assistant. Check logs for details.")
        else:
            st.sidebar.warning("Please upload files to create an assistant.")
    else:
        # Use an existing assistant
        assistant_id = st.sidebar.text_input("Enter existing assistant ID:")
        if assistant_id:
            st.session_state.assistant_id = assistant_id
            st.sidebar.success(f"Using assistant with ID: {assistant_id}")

    # Chat interface initialization
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Display previous conversation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display download buttons if any
            if "downloads" in message:
                for file_name, file_content in message["downloads"]:
                    st.download_button(
                        label=f"Download {file_name}",
                        data=file_content,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
                    if file_name.endswith('.html'):
                        st.components.v1.html(file_content.decode(), height=300, scrolling=True)
            # Display images if any
            if "images" in message:
                for image_name, image_data in message["images"]:
                    st.image(image_data)
                    st.download_button(
                        label=f"Download {image_name}",
                        data=image_data,
                        file_name=image_name,
                        mime="image/png"
                    )

    # Chat input
    prompt = st.chat_input("You:")
    if prompt:
        # Save user's message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Check if we have an assistant to talk to
        if 'assistant_id' in st.session_state and st.session_state.assistant_id:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                # Run the asynchronous function
                print(f"Sending prompt to the assistant: {prompt}")
                response, download_links, images = asyncio.run(
                    get_agent_response(st.session_state.assistant_id, prompt)
                )
                print("Received response from assistant.")
                print(f"Assistant response text:\n{response}")

                # Display the assistant's response
                message_placeholder.markdown(response)

                # Display any downloadable files
                for file_name, file_content in download_links:
                    st.download_button(
                        label=f"Download {file_name}",
                        data=file_content,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
                    if file_name.endswith('.html'):
                        st.components.v1.html(file_content.decode(), height=300, scrolling=True)

                # Display images
                for image_name, image_data in images:
                    st.image(image_data)
                    st.download_button(
                        label=f"Download {image_name}",
                        data=image_data,
                        file_name=image_name,
                        mime="image/png"
                    )

            # Append the assistant's message to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "downloads": download_links,
                "images": images
            })
        else:
            # We do not have a valid assistant ID
            no_assistant_warning = "Please create a new assistant or enter an existing assistant ID before chatting."
            st.warning(no_assistant_warning)
            print(no_assistant_warning)

if __name__ == "__main__":
    print("Running the Streamlit app...")
    try:
        main()
    except Exception as e:
        print("Unhandled exception in main():", str(e))
        traceback.print_exc()
