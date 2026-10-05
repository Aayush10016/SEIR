import type {
  Component, ComponentType, Dependency, DependencyKind, Repository, RiskAssessmentSummary, RiskLevel,
} from '@/types'

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()

interface ComponentSeed {
  id: string
  name: string
  type: ComponentType
  packageName: string
  riskLevel: RiskLevel
}

const seeds: ComponentSeed[] = [
  { id: 'payment-controller', name: 'PaymentController', type: 'CONTROLLER', packageName: 'com.shop.payment.web', riskLevel: 'LOW' },
  { id: 'payment-service', name: 'PaymentService', type: 'SERVICE', packageName: 'com.shop.payment', riskLevel: 'HIGH' },
  { id: 'legacy-payment-service', name: 'LegacyPaymentService', type: 'SERVICE', packageName: 'com.shop.payment.legacy', riskLevel: 'MEDIUM' },
  { id: 'order-service', name: 'OrderService', type: 'SERVICE', packageName: 'com.shop.order', riskLevel: 'HIGH' },
  { id: 'checkout-service', name: 'CheckoutService', type: 'SERVICE', packageName: 'com.shop.checkout', riskLevel: 'LOW' },
  { id: 'invoice-service', name: 'InvoiceService', type: 'SERVICE', packageName: 'com.shop.invoice', riskLevel: 'MEDIUM' },
  { id: 'billing-job', name: 'BillingJob', type: 'JOB', packageName: 'com.shop.billing', riskLevel: 'UNKNOWN' },
  { id: 'user-controller', name: 'UserController', type: 'CONTROLLER', packageName: 'com.shop.user.web', riskLevel: 'LOW' },
]

/** [source, target, kind]: source depends on target. This is the single source of truth for all relationship counts. */
const edges: Array<[string, string, DependencyKind]> = [
  ['payment-controller', 'payment-service', 'INJECTS'],
  ['payment-service', 'legacy-payment-service', 'CALLS'],
  ['payment-service', 'order-service', 'CALLS'],
  ['payment-service', 'invoice-service', 'CALLS'],
  ['order-service', 'legacy-payment-service', 'CALLS'],
  ['invoice-service', 'legacy-payment-service', 'IMPORTS'],
  ['checkout-service', 'order-service', 'CALLS'],
  ['checkout-service', 'payment-service', 'CONFIG_REFERENCE'],
  ['billing-job', 'invoice-service', 'CALLS'],
  ['billing-job', 'legacy-payment-service', 'CONFIG_REFERENCE'],
  ['user-controller', 'order-service', 'CALLS'],
]

export const mockDependencies: Dependency[] = edges.map(([sourceId, targetId, kind]) => ({
  id: `${sourceId}->${targetId}`,
  sourceId,
  targetId,
  kind,
}))

export const mockComponents: Component[] = seeds.map((seed) => ({
  ...seed,
  path: `src/main/java/${seed.packageName.split('.').join('/')}/${seed.name}.java`,
  dependencyCount: mockDependencies.filter((d) => d.sourceId === seed.id).length,
  dependentCount: new Set(mockDependencies.filter((d) => d.targetId === seed.id).map((d) => d.sourceId)).size,
}))

export const mockRepository: Repository = {
  id: 'shopapp',
  name: 'ShopApp',
  url: 'https://github.com/shopapp-demo/shopapp',
  branch: 'main',
  lastAnalyzedAt: minutesAgo(2),
  commitCount: 214,
  contributorCount: 6,
  evidenceCoverage: [
    { source: 'STATIC', status: 'AVAILABLE', detail: 'Source files parsed and dependency relationships extracted.' },
    { source: 'GIT', status: 'AVAILABLE', detail: 'Commit history analyzed for the main branch.' },
    { source: 'CONFIGURATION', status: 'AVAILABLE', detail: 'Application configuration files scanned for component references.' },
    { source: 'RUNTIME', status: 'UNAVAILABLE', detail: 'No runtime telemetry supplied.' },
  ],
}

export const mockRecentAssessments: RiskAssessmentSummary[] = [
  { id: 'ra-legacy-remove', componentId: 'legacy-payment-service', changeType: 'REMOVE', level: 'MEDIUM', confidence: 0.87, assessedAt: minutesAgo(5) },
  { id: 'ra-payment-refactor', componentId: 'payment-service', changeType: 'REFACTOR', level: 'HIGH', confidence: 0.91, assessedAt: minutesAgo(22) },
  { id: 'ra-user-modify', componentId: 'user-controller', changeType: 'MODIFY', level: 'LOW', confidence: 0.78, assessedAt: minutesAgo(61) },
]
