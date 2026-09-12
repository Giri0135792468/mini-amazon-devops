output "namespace" {
  description = "Common Kubernetes namespace for Mini Amazon"
  value       = kubernetes_namespace.mini.metadata[0].name
}