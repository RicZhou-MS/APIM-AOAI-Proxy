# APIM-AOAI-Proxy

Setup APIM as Azure OpenAI proxy, capture tokens and store at DB for reporting. **APIM can be created and configured at Global Azure or sovereign cloud (e.g. Azure operated by 21Vianet)**. This article illustrated using 21Vianet Azure cloud host APIM for the solution, if you host APIM at global Azure, the steps should be almost the same.

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
- **SQL Database**: Any SKU can be chosen depends on your workload, meanwhile configure appropriate firewall rule which can allow access from your Azure Function App, your tool machine, as well as Power BI service. [content](DBScript/aoaieventdb.sql)
