import asyncio
import base64
import json
import traceback
import nest_asyncio
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit as st

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

openai_api_key = st.secrets["api_keys"]["openai_api_key"]
proxy_api_key = st.secrets["api_keys"]["proxy_api_key"]

# Initialize the OpenAI client with the secure API key
client = OpenAI(api_key=openai_api_key)

# Global thread initialization
if 'user_thread' not in st.session_state:
    st.session_state.user_thread = client.beta.threads.create()

# Proxy setup
PROXY_URL = 'https://proxy.scrapeops.io/v1/'
API_KEY = proxy_api_key

def scrape_content(url):
    """Fetches HTML from the target URL using the proxy service, extracts text content, and deduplicates href links."""
    params = {
        'api_key': API_KEY,
        'url': url,
        'render_js': 'false',
        'residential': 'true',
    }
    
    try:
        with st.spinner(f"Scraping content from {url}..."):
            # Make the request to the proxy service
            response = requests.get(PROXY_URL, params=params)
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
    {"type": "code_interpreter"},
    {"type": "file_search"}
]

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

# Function to create an assistant, now receiving language-specific instructions
def create_assistant(file_ids, instructions):
    assistant = client.beta.assistants.create(
        name="Q&A AI assistant",
        instructions=instructions,
        model="gpt-4o-2024-11-20",
        tools=tools,
        tool_resources={
            'file_search': {
                'vector_stores': [{
                    'file_ids': file_ids
                }]
            }
        }
    )
    return assistant.id

def safe_tool_call(func, tool_name, **kwargs):
    """Safely execute a tool call and handle exceptions."""
    try:
        result = func(**kwargs)
        return result if result is not None else f"No content returned from {tool_name}"
    except Exception as e:
        st.error(f"Error in {tool_name}: {str(e)}")
        return f"Error occurred in {tool_name}: {str(e)}"
    
def handle_tool_outputs(run):
    """Function to handle tool outputs (scrape_content, code_interpreter, etc.)."""
    tool_outputs = []
    try:
        for call in run.required_action.submit_tool_outputs.tool_calls:
            function_name = call.function.name
            function = available_functions.get(function_name)
            if not function:
                raise ValueError(f"Function {function_name} not found in available_functions.")
            arguments = json.loads(call.function.arguments)
            # Use safe_tool_call if necessary
            with st.spinner(f"Executing a detailed search..."):
                output = safe_tool_call(function, function_name, **arguments)

            tool_outputs.append({
                "tool_call_id": call.id,
                "output": json.dumps(output)
            })

        # Use the correct user-specific thread ID here
        return client.beta.threads.runs.submit_tool_outputs(
            thread_id=st.session_state.user_thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
    except Exception as e:
        st.error(f"Error in handle_tool_outputs: {str(e)}")
        st.error(traceback.format_exc())
        return None

# Function to get agent response
async def get_agent_response(assistant_id, user_message):
    try:
        with st.spinner("Processing your request..."):
            # Use the unique thread for each session
            client.beta.threads.messages.create(
                thread_id=st.session_state.user_thread.id,
                role="user",
                content=user_message,
            )

            run = client.beta.threads.runs.create(
                thread_id=st.session_state.user_thread.id,
                assistant_id=assistant_id,
            )

            while run.status in ["queued", "in_progress"]:
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.user_thread.id,
                    run_id=run.id
                )
                if run.status == "requires_action":
                    run = handle_tool_outputs(run)
                await asyncio.sleep(1)

            last_message = client.beta.threads.messages.list(thread_id=st.session_state.user_thread.id, limit=1).data[0]

            formatted_response_text = ""
            download_links = []
            images = []

            if last_message.role == "assistant":
                for content in last_message.content:
                    if content.type == "text":
                        formatted_response_text += content.text.value
                        for annotation in content.text.annotations:
                            if annotation.type == "file_path":
                                file_id = annotation.file_path.file_id
                                file_name = annotation.text.split('/')[-1]
                                file_content = client.files.content(file_id).read()
                                download_links.append((file_name, file_content))
                    elif content.type == "image_file":
                        file_id = content.image_file.file_id
                        image_data = client.files.content(file_id).read()
                        images.append((f"{file_id}.png", image_data))
                        formatted_response_text += f"[Image generated: {file_id}.png]\n"
            else:
                formatted_response_text = "Error: No assistant response"

            return formatted_response_text, download_links, images
    except Exception as e:
        st.error(f"Error in get_agent_response: {str(e)}")
        st.error(traceback.format_exc())
        return f"Error: {str(e)}", [], []

# Streamlit app
def main():
    st.title("Q&A AI assistant")

    # Choose language
    st.sidebar.title("Language Selection")
    language_choice = st.sidebar.radio("Please choose a language:", ["English", "German"])

    

    # Sidebar for assistant selection
    st.sidebar.title("Assistant Configuration")
    assistant_choice = st.sidebar.radio("Choose an option:", ["Create New Assistant", "Use Existing Assistant"])
    if language_choice == "German":
        st.sidebar.subheader("Upload German documents")
    else:
        st.sidebar.subheader("Upload files")

    # Depending on the choice, pick the instructions
    if language_choice == "German":
        current_instructions = german_instructions
    else:
        current_instructions = english_instructions
    if assistant_choice == "Create New Assistant":
        uploaded_files = st.sidebar.file_uploader(
            "You can upload multiple files here", accept_multiple_files=True
        )
        file_ids = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_info = client.files.create(file=uploaded_file, purpose='assistants')
                file_ids.append(file_info.id)

        if file_ids:
            if st.sidebar.button("Create New Assistant"):
                st.session_state.assistant_id = create_assistant(file_ids, current_instructions)
                st.sidebar.success(f"New assistant created with ID: {st.session_state.assistant_id}")
        else:
            st.sidebar.warning("Please upload files to create an assistant.")
    else:
        # Use an existing assistant
        assistant_id = st.sidebar.text_input("Enter existing assistant ID:")
        if assistant_id:
            st.session_state.assistant_id = assistant_id
            st.sidebar.success(f"Using assistant with ID: {assistant_id}")

    # Chat interface
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
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
            if "images" in message:
                for image_name, image_data in message["images"]:
                    st.image(image_data)
                    st.download_button(
                        label=f"Download {image_name}",
                        data=image_data,
                        file_name=image_name,
                        mime="image/png"
                    )

    if prompt := st.chat_input("You:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if 'assistant_id' in st.session_state:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response, download_links, images = asyncio.run(
                    get_agent_response(st.session_state.assistant_id, prompt)
                )
                message_placeholder.markdown(response)
                
                for file_name, file_content in download_links:
                    st.download_button(
                        label=f"Download {file_name}",
                        data=file_content,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
                    if file_name.endswith('.html'):
                        st.components.v1.html(file_content.decode(), height=300, scrolling=True)
                
                for image_name, image_data in images:
                    st.image(image_data)
                    st.download_button(
                        label=f"Download {image_name}",
                        data=image_data,
                        file_name=image_name,
                        mime="image/png"
                    )
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "downloads": download_links,
                "images": images
            })
        else:
            st.warning("Please create a new assistant or enter an existing assistant ID before chatting.")

if __name__ == "__main__":
    main()
