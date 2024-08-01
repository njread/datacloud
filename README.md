# Contract Management System

This project is a Python-based application that integrates with Box's API to manage metadata templates for various contract types. The application leverages AI to extract key contract information, apply relevant metadata templates, and update Salesforce with the extracted information. The system is designed to handle contracts from multiple domains, including player contracts and university agreements.

## Table of Contents

- [Features](#features)
- [Environment Setup](#environment-setup)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Metadata Extraction:** Utilizes Box's AI capabilities to extract metadata from contracts.
- **Template Management:** Supports multiple metadata templates tailored to different contract types.
- **Salesforce Integration:** Automatically updates Salesforce with extracted metadata.
- **Dynamic Schema Handling:** Dynamically adjusts to different metadata schemas and contract types.

## Environment Setup

1. **Box Environment Setup:**
   - Ensure you have a Box environment set up with the correct API scope. This includes enabling the necessary API permissions for metadata templates, AI extraction, and file management.
   - Generate the appropriate access tokens from the Box developer console.

2. **Heroku Configuration:**
   - Deploy the application to Heroku. Ensure that the Box access tokens and any other sensitive environment variables are securely added to the Heroku environment settings.

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/contract-management.git
    cd contract-management
    ```

2. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Environment Variables:**

   Set up the following environment variables:

    - `SALESFORCE_DATA_CLOUD_ENDPOINT`: Salesforce endpoint for data updates.
    - `SALESFORCE_ACCESS_TOKEN`: Access token for authenticating with Salesforce.
    - `BOX_API_TOKEN`: Access token for authenticating with Box API.

   These should be configured within your Heroku environment settings to avoid exposing sensitive data.

## Usage

1. **Running the Application:**

    Start the Flask application using the following command:

    ```bash
    python app.py
    ```

2. **Webhook Listener:**

   The application is designed to handle incoming Box webhooks for file events such as `FILE.UPLOADED` and `FILE.PREVIEWED`. When an event is received, the appropriate metadata template is applied, and the data is sent to Salesforce.

3. **Adding New Metadata Templates:**

   The system is pre-configured with extractors for several metadata templates, such as `contractAi`, `playerContract`, and `universityAgreement`. If you need to add a new template, follow the pattern in the `utils.py` file and create a corresponding extraction function.

## Contributing

We welcome contributions to improve this project. To contribute:

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push the branch (`git push origin feature-name`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
