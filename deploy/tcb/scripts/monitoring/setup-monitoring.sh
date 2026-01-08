#!/bin/bash
# SuperInsight TCB Enterprise Monitoring Setup
# Integrates Prometheus + Grafana with multi-tenant isolation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
MONITORING_CONFIG_DIR="${SCRIPT_DIR}/../config/monitoring"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
ENVIRONMENT=""
ENABLE_MULTI_TENANT=true
ENABLE_ALERTING=true
ENABLE_GRAFANA=true
DRY_RUN=false
FORCE_SETUP=false

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

SuperInsight TCB Enterprise Monitoring Setup

OPTIONS:
    -e, --environment ENV       Target environment (development|staging|production)
    -t, --disable-multi-tenant  Disable multi-tenant monitoring
    -a, --disable-alerting      Disable alerting setup
    -g, --disable-grafana       Disable Grafana setup
    -d, --dry-run              Show what would be done without executing
    -f, --force                Force setup (overwrite existing configs)
    --help                     Show this help message

EXAMPLES:
    # Setup monitoring for production
    $0 -e production

    # Setup basic monitoring without multi-tenant features
    $0 -e development --disable-multi-tenant

    # Dry run for staging
    $0 -e staging --dry-run

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--disable-multi-tenant)
                ENABLE_MULTI_TENANT=false
                shift
                ;;
            -a|--disable-alerting)
                ENABLE_ALERTING=false
                shift
                ;;
            -g|--disable-grafana)
                ENABLE_GRAFANA=false
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE_SETUP=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

validate_inputs() {
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment not specified"
        show_usage
        exit 1
    fi
    
    local valid_envs=("development" "staging" "production")
    if [[ ! " ${valid_envs[@]} " =~ " ${ENVIRONMENT} " ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
}

load_environment_config() {
    local env_file="${SCRIPT_DIR}/../env/${ENVIRONMENT}.env"
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment configuration not found: $env_file"
        exit 1
    fi
    
    set -a
    source "$env_file"
    set +a
    
    log_info "Environment configuration loaded for: $ENVIRONMENT"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "kubectl" "jq" "envsubst")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check if running in TCB environment
    if [[ -z "${TCB_ENV_ID:-}" ]]; then
        log_warning "TCB_ENV_ID not set, assuming local development"
    fi
    
    log_success "Prerequisites check passed"
}

create_monitoring_namespace() {
    log_info "Creating monitoring namespace..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create monitoring namespace"
        return 0
    fi
    
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f - || {
        log_warning "Monitoring namespace might already exist"
    }
    
    log_success "Monitoring namespace ready"
}

setup_prometheus_config() {
    log_info "Setting up Prometheus configuration..."
    
    local prometheus_config="/tmp/prometheus-config.yaml"
    
    # Substitute environment variables in the config template
    envsubst < "${MONITORING_CONFIG_DIR}/prometheus-config.yaml" > "$prometheus_config"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create Prometheus config:"
        cat "$prometheus_config"
        return 0
    fi
    
    # Create ConfigMap for Prometheus configuration
    kubectl create configmap prometheus-config \
        --from-file=prometheus.yml="$prometheus_config" \
        --namespace=monitoring \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Prometheus configuration created"
}

setup_alert_rules() {
    if [[ "$ENABLE_ALERTING" == "false" ]]; then
        log_info "Alerting disabled, skipping alert rules setup"
        return 0
    fi
    
    log_info "Setting up alert rules..."
    
    local alert_rules="/tmp/alert-rules.yaml"
    
    # Substitute environment variables in alert rules
    envsubst < "${MONITORING_CONFIG_DIR}/alert-rules.yaml" > "$alert_rules"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create alert rules"
        return 0
    fi
    
    # Create ConfigMap for alert rules
    kubectl create configmap prometheus-alert-rules \
        --from-file=alert_rules.yml="$alert_rules" \
        --namespace=monitoring \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Alert rules configured"
}

deploy_prometheus() {
    log_info "Deploying Prometheus..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy Prometheus"
        return 0
    fi
    
    # Create Prometheus deployment
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
  labels:
    app: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:v2.45.0
        args:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus/'
          - '--web.console.libraries=/etc/prometheus/console_libraries'
          - '--web.console.templates=/etc/prometheus/consoles'
          - '--storage.tsdb.retention.time=15d'
          - '--web.enable-lifecycle'
          - '--web.enable-admin-api'
        ports:
        - containerPort: 9090
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        volumeMounts:
        - name: prometheus-config
          mountPath: /etc/prometheus/
        - name: prometheus-alert-rules
          mountPath: /etc/prometheus/rules/
        - name: prometheus-storage
          mountPath: /prometheus/
      volumes:
      - name: prometheus-config
        configMap:
          name: prometheus-config
      - name: prometheus-alert-rules
        configMap:
          name: prometheus-alert-rules
      - name: prometheus-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: monitoring
  labels:
    app: prometheus
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
    name: web
  type: ClusterIP
EOF
    
    log_success "Prometheus deployed"
}

setup_grafana_config() {
    if [[ "$ENABLE_GRAFANA" == "false" ]]; then
        log_info "Grafana disabled, skipping setup"
        return 0
    fi
    
    log_info "Setting up Grafana configuration..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would setup Grafana configuration"
        return 0
    fi
    
    # Create Grafana datasource configuration
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      access: proxy
      url: http://prometheus:9090
      isDefault: true
      editable: true
    - name: Loki
      type: loki
      access: proxy
      url: http://loki:3100
      editable: true
EOF
    
    # Create Grafana dashboard configuration
    kubectl create configmap grafana-dashboards \
        --from-file="${MONITORING_CONFIG_DIR}/grafana-dashboards.json" \
        --namespace=monitoring \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Grafana configuration created"
}

deploy_grafana() {
    if [[ "$ENABLE_GRAFANA" == "false" ]]; then
        return 0
    fi
    
    log_info "Deploying Grafana..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy Grafana"
        return 0
    fi
    
    # Create Grafana deployment
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
  labels:
    app: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.0.0
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "${GRAFANA_ADMIN_PASSWORD:-admin123}"
        - name: GF_USERS_ALLOW_SIGN_UP
          value: "false"
        - name: GF_AUTH_ANONYMOUS_ENABLED
          value: "false"
        - name: GF_INSTALL_PLUGINS
          value: "grafana-piechart-panel,grafana-worldmap-panel"
        ports:
        - containerPort: 3000
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        volumeMounts:
        - name: grafana-datasources
          mountPath: /etc/grafana/provisioning/datasources/
        - name: grafana-dashboards-config
          mountPath: /etc/grafana/provisioning/dashboards/
        - name: grafana-dashboards
          mountPath: /var/lib/grafana/dashboards/
        - name: grafana-storage
          mountPath: /var/lib/grafana/
      volumes:
      - name: grafana-datasources
        configMap:
          name: grafana-datasources
      - name: grafana-dashboards-config
        configMap:
          name: grafana-dashboard-config
      - name: grafana-dashboards
        configMap:
          name: grafana-dashboards
      - name: grafana-storage
        emptyDir: {}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-config
  namespace: monitoring
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
    - name: 'default'
      orgId: 1
      folder: ''
      type: file
      disableDeletion: false
      updateIntervalSeconds: 10
      options:
        path: /var/lib/grafana/dashboards
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: monitoring
  labels:
    app: grafana
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
    name: web
  type: ClusterIP
EOF
    
    log_success "Grafana deployed"
}

setup_multi_tenant_monitoring() {
    if [[ "$ENABLE_MULTI_TENANT" == "false" ]]; then
        log_info "Multi-tenant monitoring disabled"
        return 0
    fi
    
    log_info "Setting up multi-tenant monitoring..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would setup multi-tenant monitoring"
        return 0
    fi
    
    # Create tenant discovery service
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tenant-discovery
  namespace: monitoring
  labels:
    app: tenant-discovery
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tenant-discovery
  template:
    metadata:
      labels:
        app: tenant-discovery
    spec:
      containers:
      - name: tenant-discovery
        image: ${REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-latest
        command: ["python", "-m", "src.monitoring.tenant_discovery"]
        env:
        - name: ENVIRONMENT
          value: "${ENVIRONMENT}"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: tenant-discovery
  namespace: monitoring
  labels:
    app: tenant-discovery
spec:
  selector:
    app: tenant-discovery
  ports:
  - port: 8080
    targetPort: 8080
    name: http
  type: ClusterIP
EOF
    
    log_success "Multi-tenant monitoring configured"
}

setup_alertmanager() {
    if [[ "$ENABLE_ALERTING" == "false" ]]; then
        return 0
    fi
    
    log_info "Setting up Alertmanager..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would setup Alertmanager"
        return 0
    fi
    
    # Create Alertmanager configuration
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'localhost:587'
      smtp_from: 'alerts@superinsight.ai'
    
    route:
      group_by: ['alertname', 'environment', 'tenant_id']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'web.hook'
      routes:
      - match:
          severity: critical
        receiver: 'critical-alerts'
      - match:
          category: security
        receiver: 'security-alerts'
      - match_re:
          tenant_id: '.+'
        receiver: 'tenant-alerts'
    
    receivers:
    - name: 'web.hook'
      webhook_configs:
      - url: '${SLACK_WEBHOOK_URL:-http://localhost:9093/webhook}'
        send_resolved: true
    
    - name: 'critical-alerts'
      webhook_configs:
      - url: '${SLACK_WEBHOOK_URL:-http://localhost:9093/webhook}'
        send_resolved: true
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
    
    - name: 'security-alerts'
      webhook_configs:
      - url: '${SECURITY_WEBHOOK_URL:-http://localhost:9093/webhook}'
        send_resolved: true
        title: 'SECURITY: {{ .GroupLabels.alertname }}'
    
    - name: 'tenant-alerts'
      webhook_configs:
      - url: 'http://tenant-discovery:8080/alerts/{{ .GroupLabels.tenant_id }}'
        send_resolved: true
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alertmanager
  namespace: monitoring
  labels:
    app: alertmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alertmanager
  template:
    metadata:
      labels:
        app: alertmanager
    spec:
      containers:
      - name: alertmanager
        image: prom/alertmanager:v0.25.0
        args:
          - '--config.file=/etc/alertmanager/alertmanager.yml'
          - '--storage.path=/alertmanager'
          - '--web.external-url=http://localhost:9093'
        ports:
        - containerPort: 9093
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        volumeMounts:
        - name: alertmanager-config
          mountPath: /etc/alertmanager/
        - name: alertmanager-storage
          mountPath: /alertmanager/
      volumes:
      - name: alertmanager-config
        configMap:
          name: alertmanager-config
      - name: alertmanager-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager
  namespace: monitoring
  labels:
    app: alertmanager
spec:
  selector:
    app: alertmanager
  ports:
  - port: 9093
    targetPort: 9093
    name: web
  type: ClusterIP
EOF
    
    log_success "Alertmanager configured"
}

verify_deployment() {
    log_info "Verifying monitoring deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would verify deployment"
        return 0
    fi
    
    # Wait for deployments to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring || {
        log_error "Prometheus deployment failed to become ready"
        return 1
    }
    
    if [[ "$ENABLE_GRAFANA" == "true" ]]; then
        kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring || {
            log_error "Grafana deployment failed to become ready"
            return 1
        }
    fi
    
    if [[ "$ENABLE_ALERTING" == "true" ]]; then
        kubectl wait --for=condition=available --timeout=300s deployment/alertmanager -n monitoring || {
            log_error "Alertmanager deployment failed to become ready"
            return 1
        }
    fi
    
    # Test Prometheus connectivity
    local prometheus_pod
    prometheus_pod=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}')
    
    if kubectl exec -n monitoring "$prometheus_pod" -- wget -q -O- http://localhost:9090/-/healthy | grep -q "Prometheus is Healthy"; then
        log_success "Prometheus is healthy"
    else
        log_error "Prometheus health check failed"
        return 1
    fi
    
    log_success "Monitoring deployment verified"
}

print_access_info() {
    log_info "Monitoring Access Information"
    echo "================================"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Access information would be displayed here"
        return 0
    fi
    
    echo "Prometheus: kubectl port-forward -n monitoring svc/prometheus 9090:9090"
    echo "  Access at: http://localhost:9090"
    
    if [[ "$ENABLE_GRAFANA" == "true" ]]; then
        echo "Grafana: kubectl port-forward -n monitoring svc/grafana 3000:3000"
        echo "  Access at: http://localhost:3000"
        echo "  Username: admin"
        echo "  Password: ${GRAFANA_ADMIN_PASSWORD:-admin123}"
    fi
    
    if [[ "$ENABLE_ALERTING" == "true" ]]; then
        echo "Alertmanager: kubectl port-forward -n monitoring svc/alertmanager 9093:9093"
        echo "  Access at: http://localhost:9093"
    fi
    
    echo ""
    echo "To expose services externally, configure TCB ingress or load balancer."
}

main() {
    parse_args "$@"
    validate_inputs
    load_environment_config
    check_prerequisites
    
    log_info "Setting up enterprise monitoring for environment: $ENVIRONMENT"
    
    create_monitoring_namespace
    setup_prometheus_config
    setup_alert_rules
    deploy_prometheus
    setup_grafana_config
    deploy_grafana
    setup_multi_tenant_monitoring
    setup_alertmanager
    
    verify_deployment
    print_access_info
    
    log_success "Enterprise monitoring setup completed successfully!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi