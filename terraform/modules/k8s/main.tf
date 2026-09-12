resource "kubernetes_namespace" "mini" {
  metadata {
    name = var.namespace
  }
}