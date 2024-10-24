param location string
param projectcode string

var keyVaultName = '${projectcode}-z-dev-kv2'
var searchName = '${projectcode}-z-dev-ais'
var openAIName = '${projectcode}-z-dev-oai'
var cosmosName = '${projectcode}-z-dev-csdb'
var storageAccountName = '${projectcode}zdevsa'
var appServicePlanName = '${projectcode}-z-dev-asp'
var functionAppName = '${projectcode}-z-dev-func'
var storageAccountFunctionName = '${toLower('${projectcode}${uniqueString(resourceGroup().id, functionAppName)}func')}'
var appInsightsName = '${projectcode}-z-dev-ai'
var webAppName = '${projectcode}-z-dev-webapp'

resource azure_key_vault 'Microsoft.KeyVault/vaults@2019-09-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'premium'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 7
    enableRbacAuthorization: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource azure_search_service 'Microsoft.Search/searchServices@2020-08-01' = {
  name: searchName
  location: location
  sku: {
    name: 'standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

resource open_ai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAIName
  location: 'canadaeast'
  kind: 'OpenAI'
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: 'aoai-${openAIName}'
  }
  sku: {
    name: 'S0'
  }
}

resource cosmos_db_account 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    locations: [
      {
        locationName: location
      }
    ]
    databaseAccountOfferType: 'Standard'
    publicNetworkAccess: 'Enabled'
  }
}

resource azure_storage_account_data 'Microsoft.Storage/storageAccounts@2019-06-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    isHnsEnabled: true
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices, Logging, Metrics'
    }
  }
}

resource azure_app_service_plan 'Microsoft.Web/serverfarms@2020-06-01' = {
  name: appServicePlanName
  location: location
  kind: 'Linux'
  sku: {
    tier: 'PremiumV3'
    name: 'P1v3'
    family: 'Pv3'
    capacity: 1
    size: 'P1v3'
  }
  properties: {
    reserved: true
  }
}

resource azure_storage_account_function 'Microsoft.Storage/storageAccounts@2021-02-01' = {
  name: storageAccountFunctionName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    isHnsEnabled: true
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices, Logging, Metrics'
    }
  }
}

resource app_insights 'Microsoft.Insights/components@2015-05-01' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource azure_function_app 'Microsoft.Web/sites@2021-02-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: azure_app_service_plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${azure_storage_account_function.name};AccountKey=${listKeys(azure_storage_account_function.id, '2021-02-01').keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${azure_storage_account_function.name};AccountKey=${listKeys(azure_storage_account_function.id, '2021-02-01').keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: app_insights.properties.InstrumentationKey
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '0' 
        }
      ]
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
    }
  }
}

resource azure_web_app 'Microsoft.Web/sites@2021-02-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: azure_app_service_plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'NODE|18-lts' 
      appSettings: [
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: app_insights.properties.InstrumentationKey
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '18-lts'
        }
      ]
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
    }
  }
}

output functionAppHostName string = azure_function_app.properties.defaultHostName
output webAppHostName string = azure_web_app.properties.defaultHostName

