# APIM-AOAI-Proxy

Setup APIM as Azure OpenAI proxy, capture tokens and store at DB for company internal billing for BU cross charge. **APIM can be created and configured at Global Azure or sovereign cloud (e.g. Azure operated by 21Vianet)**. This article illustrated using 21Vianet Azure cloud host APIM for the solution, if you host APIM at global Azure, the steps should be almost the same.

In terms of Azure OpenAI stream call, this solution **supports APIM to capture stream response payload** and calculate the tokens at downstream Function API tier, however enable APIM capture stream response payload will seriously impact end-user experience because the Server-send event (SSE) stream has to be cached at APIM for payload capture before APIM forward the flow to client, therefore client will NOT see instant response flow from stream, but will wait untill the response returned as whole at the end. In other words, the behavior become like sychronized call rather than stream call.

This solution also **supports disable stream capture at APIM**, which provide streaming experience for end-user, however in this case APIM will only caputre and calculate request payload tokens, the respones payload will not be captured and calculated.

## Environment Preparation

### Tool Machine

- Install [Python](https://www.python.org/downloads/) into tool machine, here use v3.11
- Install VSCode
  - Install [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).
  - Install **Azure Account** extension. (**NOTE**: Refer to [this KB](https://docs.azure.cn/zh-cn/articles/azure-operations-guide/others/aog-others-howto-login-china-azure-by-vscode) for how to configure Vscode for login Sovereign Cloud. e.g. Azure China)
  - Install **[Azure Resources](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azureresourcegroups)** extension. Please use v0.75 rather than v0.80(preview) as v0.80 has bug and unable support sovereign cloud login at the moment I write this blog.
  - Install **Azure Function** extension.
  - Install **Azure API Management** extesion.

### Azure OpenAI

- Create Azure OpenAI instance at corresponding region
- Deploy all models needed for business
- Remeber Azure OpenAI instance endpoint (_`https://<aoai_endpoint_name>.openai.azure.com/`_) and access key _`<aoai_endpoint_access_key>`_ which will be used later

### Proxy Tier (Azure Resources)

Login Azure portal and create following resources, here use Azure China as example, use Global Azure will be technically the same.

- **API Management**: Choose Developer tier or other tiers denpends on your environment and VNET integration needs, but don't choose consumption tier.
- **Event Hub**: Any tier can be chosen.
- **Function App**: Create Azure Function App resource with below configuration
  - _Runtime stack_ - Python
  - _Version_ - 3.11
  - _Operating System_ - Linux
  - _Hosting Plan_ - any plan except Consumption plan
- **SQL Database**: Any SKU can be chosen depends on your workload, meanwhile configure appropriate firewall rule which can allow access from your Azure Function App, your tool machine, as well as Power BI service.

## Environment Setup

### SQL Database

- login the SQL Database we just created via SSMS, and execute [SQL script](DBScript/aoaieventdb.sql) to create table schema.
- There is partial of model pricing rate information provisioned into table _**AoaiTokenRate**_, you can update or provision your own version according to your model name and corresponding price.

### Event Hub

- Go to the Event Hub Namespace which just created at above steps, create a event hub instance
- Click **Shared access policies** of the instance, create a SAS Policy and give **Send** and **Listen** policy, remember the **connection string** for later use.
  ![Alt text](images/image.png)

### APIM

- Use below PowerShell cmdlet to create API Management logger. Detail information can refer to [How to log events to Azure Event Hubs in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-log-event-hubs?tabs=PowerShell)

```PowerShell
# API Management service-specific details
$apimServiceName = "<Your APIM name>"
$resourceGroupName = "<Your APIM resource group>"

# Create logger
$context = New-AzApiManagementContext -ResourceGroupName $resourceGroupName -ServiceName $apimServiceName
New-AzApiManagementLogger -Context $context -LoggerId "event-hub-logger" -Name "<your event hub name>" -ConnectionString "<your event hub connection string>" -Description "Event hub logger with connection string"
```

(**NOTE**: Make sure LoggerId set to _**event-hub-logger**_,otherwise you will need change loggerId in APIM policy at later steps accordingly)

- <a name="step1"/> Open [this github folder](https://github.com/Azure/azure-rest-api-specs/tree/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable) via browser, click into latest version folder (**2023-05-15** is the latest version folder when write this blog).
- Download the **inference.json** to tool machine. - Open **inference.json** in vscode at tool machine, change the **servers** property to make the **url** and **endpoint** properties pointing to your Azure OpenAI API instance created previously.
  ```JSON
    "servers": [
      {
      "url": "https://<aoai_endpoint_name>.openai.azure.com/openai",
      "variables": {
          "endpoint": {
          "default": "<aoai_endpoint_name>.openai.azure.com"}
          }
      }
    ],
  ```
- Import the updated **inference.json** file in APIM as below capture, select **API**, then choose **Add API**, click **OpenAPI**
  ![Alt text](images/image-1.png)
- At Create from OpenAPI specification page, choose **Full**, select and import **inference.json**, set _**openai**_ at API URL suffix field. click **Create** button.
  ![Alt text](images/image-2.png)
- When the import creation complete, click **setting**, rename the subscription key verification header as **api-key**.
  ![Alt text](images/image-3.png)
- Create a named value for your Azure OpenAI API key. To creat a named value, see [using named values in Azure API Management polices](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-properties?tabs=azure-portal). Take note of the Display name you give your named value as it is needed in next steps. Here we set the name display name as _**azure-openai-key**_. set the Type as **Secret**, and set the secret value as your Azure OpenAI endpoint access key _`<aoai_endpoint_access_key>`_ which created at previous step
  ![Alt text](images/image-4.png)
- Similarly, add another named value with Name and Display name as _**capture-streaming**_,set the Type as **Plain**, set the value as _**True**_  
  (**NOTE**: You can set it to _**False**_ if you want to only capture streaming _request_ playload without capturing _response_ payload, this will give end-user real streaming experience)
  ![Alt text](images/image-5.png)
- Go to **Products** at APIM blade menu add a new product with name **_openai-product_**.
- Click into the newly created product, add the imported OpenAI APIs into the product.
  ![Alt text](images/image-8.png)
- And also add necessary **_subscription_** for APIM API call key authentication.  
  ![Alt text](images/image-7.png)
  (**NOTE**: you can add multiple subscriptions, each subscription can be assigned to individual end-user for calling OpenAI API via this APIM instance)
- Select each **subscription** and **show the key**, note the key and share with corresponding end-user, this key will work as **_OpenAI access key_** for OpenAI API call via APIM.
  ![Alt text](images/image-6.png)
- Click **Policies** in this Product, and then click the **edit policy icon** as below capture
  ![Alt text](images/image-9.png)
- Copy all the policies from [this policy file](<APIM*Product_Policy/TokenCaptureProduct(parent).xml>), and paste into current policy edit page content, and **Save** the policy
  ![Alt text](images/image-10.png)
  **NOTE**: If you configured different API Management logger name at previous step, you should update all relavant logger-id at all \_logger-id="**event-hub-logger**"* accordingly before Save.

### Function App

- click to [previous step](#step1)
  (**NOTE**: [How To Create and Deploy a Python Azure Function Using Azure DevOps CI/CD](https://medium.com/globant/how-to-create-and-deploy-a-python-azure-function-using-azure-devops-ci-cd-2aa8f8675716))
