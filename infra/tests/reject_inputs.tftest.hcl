mock_provider "oci" {
  mock_data "oci_identity_availability_domains" {
    defaults = {
      availability_domains = [
        {
          compartment_id = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          id             = "ocid1.availabilitydomain.oc1..aaaa"
          name           = "xxxx:SA-SAOPAULO-1-AD-1"
        }
      ]
    }
  }

  mock_data "oci_core_images" {
    defaults = {
      images = [
        {
          agent_features           = []
          base_image_id            = ""
          billable_size_in_gbs     = "0"
          compartment_id           = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          create_image_allowed     = false
          defined_tags             = {}
          display_name             = "Canonical-Ubuntu-24.04-aarch64-2026.09.01-0"
          freeform_tags            = {}
          id                       = "ocid1.image.oc1.sa-saopaulo-1.dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
          image_source_details     = []
          instance_id              = ""
          launch_mode              = "NATIVE"
          launch_options           = []
          listing_type             = "NONE"
          operating_system         = "Canonical Ubuntu"
          operating_system_version = "24.04"
          size_in_mbs              = "0"
          state                    = "AVAILABLE"
          time_created             = "2026-09-01T00:00:00Z"
        }
      ]
    }
  }
}

variables {
  compartment_ocid                 = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  region                           = "sa-saopaulo-1"
  home_region                      = "sa-saopaulo-1"
  home_region_confirmed            = true
  manual_limits_checked            = true
  public_ipv4_pricing_acknowledged = true
  availability_domain              = "xxxx:SA-SAOPAULO-1-AD-1"
  name                             = "homelab"
  instance_shape                   = "VM.Standard.A1.Flex"
  ocpus                            = 2
  memory_gb                        = 12
  boot_volume_gb                   = 50
  boot_volume_vpus_per_gb          = 10
  assign_ephemeral_public_ipv4     = true
  admin_cidr                       = "8.8.8.8/32"
  ssh_public_key                   = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8g homelab-test"
  image_id                         = null
}

run "recusa_ssh_aberto_para_a_internet" {
  command = plan
  variables {
    admin_cidr = "0.0.0.0/0"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_prefixo_maior_que_24" {
  command = plan
  variables {
    admin_cidr = "8.8.8.0/23"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_cidr_nao_canonico" {
  command = plan
  variables {
    admin_cidr = "8.8.8.8/24"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_rede_privada" {
  command = plan
  variables {
    admin_cidr = "10.1.2.0/24"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_rede_privada_172" {
  command = plan
  variables {
    admin_cidr = "172.16.5.0/24"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_rede_privada_192" {
  command = plan
  variables {
    admin_cidr = "192.168.1.10/32"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_loopback" {
  command = plan
  variables {
    admin_cidr = "127.0.0.1/32"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_link_local" {
  command = plan
  variables {
    admin_cidr = "169.254.1.1/32"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_cgnat" {
  command = plan
  variables {
    admin_cidr = "100.64.0.0/24"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_documentacao" {
  command = plan
  variables {
    admin_cidr = "203.0.113.10/32"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_multicast" {
  command = plan
  variables {
    admin_cidr = "224.0.0.1/32"
  }
  expect_failures = [var.admin_cidr]
}

run "recusa_quatro_ocpus" {
  command = plan
  variables {
    ocpus = 4
  }
  expect_failures = [var.ocpus]
}

run "recusa_24_gb" {
  command = plan
  variables {
    memory_gb = 24
  }
  expect_failures = [var.memory_gb]
}

run "recusa_memoria_abaixo_de_um_gb_por_ocpu" {
  command = plan
  variables {
    ocpus     = 2
    memory_gb = 1
  }
  expect_failures = [var.memory_gb]
}

run "recusa_boot_de_47_gb" {
  command = plan
  variables {
    boot_volume_gb = 47
  }
  expect_failures = [var.boot_volume_gb]
}

run "recusa_boot_de_200_gb" {
  command = plan
  variables {
    boot_volume_gb = 200
  }
  expect_failures = [var.boot_volume_gb]
}

run "recusa_vpu_maior" {
  command = plan
  variables {
    boot_volume_vpus_per_gb = 20
  }
  expect_failures = [var.boot_volume_vpus_per_gb]
}

run "recusa_outra_shape" {
  command = plan
  variables {
    instance_shape = "VM.Standard.E4.Flex"
  }
  expect_failures = [var.instance_shape]
}

run "recusa_regiao_diferente_da_home" {
  command = plan
  variables {
    region = "us-ashburn-1"
  }
  expect_failures = [var.home_region]
}

run "recusa_home_region_sem_confirmacao" {
  command = plan
  variables {
    home_region_confirmed = false
  }
  expect_failures = [var.home_region_confirmed]
}

run "recusa_sem_conferencia_de_cota" {
  command = plan
  variables {
    manual_limits_checked = false
  }
  expect_failures = [var.manual_limits_checked]
}

run "recusa_sem_ciencia_do_preco_ipv4" {
  command = plan
  variables {
    public_ipv4_pricing_acknowledged = false
  }
  expect_failures = [var.public_ipv4_pricing_acknowledged]
}

run "recusa_sem_ipv4_efemero" {
  command = plan
  variables {
    assign_ephemeral_public_ipv4 = false
  }
  expect_failures = [var.assign_ephemeral_public_ipv4]
}

run "recusa_chave_privada" {
  command = plan
  variables {
    ssh_public_key = "-----BEGIN OPENSSH PRIVATE KEY----- abc"
  }
  expect_failures = [var.ssh_public_key]
}

run "recusa_chave_privada_adicional" {
  command = plan
  variables {
    additional_ssh_public_keys = [
      {
        label      = "automation"
        public_key = "-----BEGIN OPENSSH PRIVATE KEY----- abc"
      }
    ]
  }
  expect_failures = [var.additional_ssh_public_keys]
}

run "recusa_chave_adicional_repetida" {
  command = plan
  variables {
    additional_ssh_public_keys = [
      {
        label      = "automation"
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8g homelab-test"
      }
    ]
  }
  expect_failures = [var.additional_ssh_public_keys]
}

run "recusa_ocid_de_instancia_como_compartment" {
  command = plan
  variables {
    compartment_ocid = "ocid1.instance.oc1.sa-saopaulo-1.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.compartment_ocid]
}

run "recusa_ocid_de_usuario_como_compartment" {
  command = plan
  variables {
    compartment_ocid = "ocid1.user.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.compartment_ocid]
}

run "recusa_tenancy_com_regiao" {
  command = plan
  variables {
    compartment_ocid = "ocid1.tenancy.oc1.sa-saopaulo-1.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.compartment_ocid]
}

run "recusa_compartment_sem_regiao_em_branco" {
  command = plan
  variables {
    compartment_ocid = "ocid1.compartment.oc1.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.compartment_ocid]
}

run "recusa_tenancy_de_outro_realm" {
  command = plan
  variables {
    compartment_ocid = "ocid1.tenancy.oc2..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.compartment_ocid]
}

run "recusa_imagem_de_outra_regiao" {
  command = plan
  variables {
    image_id = "ocid1.image.oc1.iad.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.image_id]
}
