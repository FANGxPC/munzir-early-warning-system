// Munzir (منذر) - Infrastructure as Code (Bicep) for Azure for Students
// Deploys Serverless Azure Container App with Scale-to-Zero ($0.00 idle cost)

@description('Location for all resources')
param location string = resourceGroup().location

@description('Prefix for resource names')
param appPrefix string = 'munzir'

@description('Container image tag to deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'

var logAnalyticsName = '${appPrefix}-logs'
var containerAppEnvName = '${appPrefix}-env'
var appName = '${appPrefix}-app'

// 1. Log Analytics Workspace (Consumption Tier)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 2. Azure Container Apps Managed Environment (Serverless Consumption)
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// 3. Azure Container App (Configured for $0 Scale-to-Zero Free Tier)
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'prahari-surveillance-engine'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'PORT'
              value: '8000'
            }
          ]
        }
      ]
      scale: {
        // CRITICAL FOR AZURE FOR STUDENTS:
        // minReplicas = 0 ensures zero credit burn when the app is idle.
        // It wakes up automatically in ~2 seconds upon incoming HTTPS traffic.
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output appFqdn string = containerApp.properties.configuration.ingress.fqdn
output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'

