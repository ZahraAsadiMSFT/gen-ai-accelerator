# Frontend

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 18.2.5.

## Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The application will automatically reload if you change any of the source files.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via a platform of your choice. To use this command, you need to first add a package that implements end-to-end testing capabilities.

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.


# Azure Deployment Steps

### Step 1: Create Azure Web App (in portal or using the provided Bicep code)

1. **Using Azure Portal**:
   - Navigate to the [Azure Portal](https://portal.azure.com/).
   - Select **Create a resource** from the left sidebar.
   - Choose **Web App** under the "Compute" section.
   - Provide the following information:
     - **Subscription**: Select your subscription.
     - **Resource Group**: Create a new one or use an existing one.
     - **Name**: Enter a unique name for your web app.
     - **Publish**: Choose **Code**.
     - **Runtime stack**: Choose **Node.js** (18 LTS).
     - **Operating System**: Select **Linux**.
     - **Region**: Select your preferred region.
     - **App Service Plan**: Choose or create your App Service Plan.
   - Click **Review + Create**, and then **Create**.

2. **Using Bicep code**:
    - Use the `deploy.bicep` template to deploy the required services.
    - After creating the resource group, run the following command using Azure Cloud Shell:
    ```bash
    az deployment group create --resource-group <resource-group-name> --template-file deploy.bicep
### Step 2: Add environment variables to the Web App

Once the Web App is created, add the following environment variables:

1. Go to **Environment variables** in the Web App settings (Azure Portal).
2. Under the **App settings** tab, click **Add** for each environment variable:
   - `EMBEDDING_API_KEY`
   - `EMBEDDING_API_URL` 

      Go to Azure OpenAI Studio -> Deployments -> ircc-embedding
   - `GENERATE_API_KEY`
   - `GENERATE_API_URL`

      Go to Azure Function -> GenerateKnowledgeScan -> Get function URL
   - `SEARCH_API_KEY`
   - `SEARCH_API_URL`

      Go to Search Service -> Url and Keys
3. Enter the appropriate key-value pairs for each setting.
4. Click **Save** after all environment variables are added.

### Step 3: Create a service principal and add GitHub Action secret

1. **Create a service principal**:
   - Open the **Azure CLI** and execute the following command:
     ```bash
     az login 
     
     az ad sp create-for-rbac --name "<service-principal-name>" --role contributor --scopes /subscriptions/<your-subscription-id>/resourceGroups/<your-resource-group> --sdk-auth
     ```
   - Replace `<service-principal-name>`, `<your-subscription-id>`, and `<your-resource-group>` with the appropriate values.
   - Copy the output JSON. It will look something like this:
     ```json
     {
       "clientId": "...",
       "clientSecret": "...",
       "subscriptionId": "...",
       "tenantId": "...",
       "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
       "resourceManagerEndpointUrl": "https://management.azure.com/",
       "activeDirectoryGraphResourceId": "https://graph.windows.net/",
       "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
       "galleryEndpointUrl": "https://gallery.azure.com/",
       "managementEndpointUrl": "https://management.core.windows.net/"
     }
     ```

2. **Add AZURE_CREDENTIALS as GitHub secret**:
   - Go to your GitHub repository.
   - Navigate to **Settings** > **Secrets and variables** > **Actions**.
   - Click **New repository secret**.
   - Name the secret **AZURE_CREDENTIALS** and paste the JSON output you copied from the service principal creation.

### Step 4: Modify the GitHub Actions workflow file and run the deployment

1. Open the `.github/workflows/` folder in project.
2. Locate the workflow file.
3. Update the `app-name` in the workflow file to match your Azure Web App name:
   ```yaml
   - name: 'Deploy to Azure Web App'
     id: deploy-to-webapp
     uses: azure/webapps-deploy@v2
     with:
       app-name: 'your-app-name' # Replace this with the name of your Azure Web App
       package: .
   ```

4. Commit the changes and push to your repository. The GitHub Actions workflow will automatically run and deploy your Angular app to the Azure Web App.

By following these steps, the IRCC Document AI Search frontend should be deployed to Azure Web App and ready to run with the specified environment variables.

### Addtional Suggestions:
1. Use managed identity for the Azure Function and CosmosDB connection. 
2. Use Key Vault for secrets. 