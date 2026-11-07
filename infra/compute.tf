data "oci_identity_availability_domains" "available" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ubuntu_arm" {
  count                    = var.image_id == null ? 1 : 0
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  state                    = "AVAILABLE"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "terraform_data" "guards" {
  input = local.selected_image_id

  lifecycle {
    precondition {
      condition     = contains(local.availability_domain_names, var.availability_domain)
      error_message = "availability_domain nao esta na lista retornada para este compartment. Valores retornados: ${join(", ", local.availability_domain_names)}. Nenhuma disponibilidade foi inventada."
    }

    precondition {
      condition     = local.selected_image_id != null
      error_message = "Nenhuma imagem Canonical Ubuntu 24.04 aarch64, compativel com VM.Standard.A1.Flex e que nao seja Minimal, foi retornada. Nao ha OCID de imagem embutido. Confira a regiao ou informe image_id so depois de ve-lo na console."
    }

    precondition {
      condition = (
        var.image_id != null ||
        (
          local.selected_image_name != null &&
          strcontains(lower(local.selected_image_name), "aarch64") &&
          !strcontains(lower(local.selected_image_name), "minimal")
        )
      )
      error_message = "A consulta automatica precisa escolher Ubuntu 24.04 aarch64 completo. Para ARM, a documentacao de imagens da OCI pede a imagem Ubuntu, nao a Minimal."
    }
  }
}

resource "oci_core_instance" "homelab" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.name
  shape               = var.instance_shape
  freeform_tags       = local.tags

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = local.selected_image_id
    boot_volume_size_in_gbs = var.boot_volume_gb
    boot_volume_vpus_per_gb = var.boot_volume_vpus_per_gb
  }

  create_vnic_details {
    subnet_id              = oci_core_subnet.public.id
    display_name           = "${var.name}-vnic"
    hostname_label         = var.name
    assign_public_ip       = var.assign_ephemeral_public_ipv4
    assign_ipv6ip          = false
    skip_source_dest_check = false
    nsg_ids                = []
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  is_pv_encryption_in_transit_enabled = true
  preserve_boot_volume                = false

  depends_on = [terraform_data.guards]

  lifecycle {
    precondition {
      condition     = local.selected_image_id != null
      error_message = "A instancia nao pode ser planejada sem uma imagem Ubuntu 24.04 ARM aceita."
    }
  }
}
