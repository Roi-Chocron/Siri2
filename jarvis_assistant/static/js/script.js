document.addEventListener('DOMContentLoaded', () => {
    const commandInput = document.getElementById('commandInput');
    const sendCommandButton = document.getElementById('sendCommandButton');
    const responseContainer = document.getElementById('responseContainer');

    // Function to add a message to the response container
    function addMessage(text, sender, isError = false) { // Added isError parameter
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'jarvis-message');

        messageDiv.textContent = text;

        // Add error class for Jarvis if isError is true or text indicates an error
        if (sender === 'jarvis') {
            // Check for explicit isError flag or common error phrases
            if (isError ||
                text.toLowerCase().includes('error:') ||
                text.toLowerCase().includes('sorry, i couldn\'t') ||
                text.toLowerCase().includes('sorry i couldn\'t') ||
                text.toLowerCase().includes('failed to') ||
                text.toLowerCase().includes('unable to')) {
                messageDiv.classList.add('error'); // Use the .error class defined in CSS for .jarvis-message.error
            }
        }

        responseContainer.appendChild(messageDiv);
        responseContainer.scrollTop = responseContainer.scrollHeight; // Auto-scroll to the latest message
    }

    // Function to send command to backend
    async function sendCommand() {
        const commandText = commandInput.value.trim();
        if (!commandText) return;

        addMessage(commandText, 'user');
        commandInput.value = ''; // Clear input field

        try {
            // Add a "Jarvis is thinking..." message
            const thinkingMsg = "J.A.R.V.I.S. is thinking...";
            addMessage(thinkingMsg, 'jarvis');

            const response = await fetch('/command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: commandText }),
            });

            // Remove "Jarvis is thinking..." message
            const messages = responseContainer.getElementsByClassName('jarvis-message');
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].textContent === thinkingMsg) {
                    messages[i].remove();
                    break;
                }
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                const errorMsg = errorData && errorData.error ? errorData.error : `Server error ${response.status}`;
                addMessage(errorMsg, 'jarvis', true); // Pass true for isError
                console.error('Server error:', errorMsg);
                return;
            }

            const data = await response.json();
            if (data.response) {
                // The error check is now primarily handled by the third argument in addMessage
                addMessage(data.response, 'jarvis');
            } else if (data.error) { // Backend explicitly sending an error field
                addMessage(data.error, 'jarvis', true);
            } else {
                addMessage("Received an unexpected response structure from J.A.R.V.I.S.", 'jarvis', true);
            }

        } catch (error) {
            // Remove "Jarvis is thinking..." message in case of network error
            const messages = responseContainer.getElementsByClassName('jarvis-message');
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].textContent === thinkingMsg) {
                    messages[i].remove();
                    break;
                }
            }
            addMessage("Network error: Could not connect to J.A.R.V.I.S. Ensure the server is running.", 'jarvis', true);
            console.error('Failed to send command:', error);
        }
    }

    // Event listeners
    sendCommandButton.addEventListener('click', sendCommand);
    commandInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendCommand();
        }
    });

    // Initial greeting from Jarvis (optional, could also be an empty state message)
    addMessage("Hello! I am J.A.R.V.I.S. How can I assist you today?", 'jarvis');
    commandInput.focus(); // Focus on input field on load
});
