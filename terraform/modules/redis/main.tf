


resource "kubernetes_stateful_set" "redis" {
   
metadata {
  name      = var.redis_name
  namespace = var.namespace

  
}

  spec {
    service_name = var.redis_name
    replicas     = 1

    selector {
      match_labels = {
        app = var.redis_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.redis_name
        }
      }

      spec {
        container {
          name  = "redis"
          image = "redis:7"

          port {
            container_port = 6379
          }

          command = [
            "redis-server",
            "--appendonly",
            "yes"
          ]

          volume_mount {
            name       = "redis-data"
            mount_path = "/data"
          }

          readiness_probe {
            exec {
              command = [
                "redis-cli",
                "ping"
              ]
            }

            initial_delay_seconds = 5
            period_seconds        = 10
          }

          liveness_probe {
            exec {
              command = [
                "redis-cli",
                "ping"
              ]
            }

            initial_delay_seconds = 15
            period_seconds        = 20
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }

            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "redis-data"
      }

      spec {
        access_modes = ["ReadWriteOnce"]

        resources {
          requests = {
            storage = "5Gi"
          }
        }
      }
    }
  }
}



resource "kubernetes_service" "redis" {

metadata {
  name      = var.redis_name
  namespace = var.namespace


}

  spec {
    cluster_ip = "None"

    selector = {
      app = var.redis_name
    }

    port {
      name        = "redis"
      port        = 6379
      target_port = 6379
    }
  }
}