mock_provider "oci" {
  mock_data "oci_identity_availability_domains" {
    defaults = {
      availability_domains = [
        {
          compartment_id = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          id             = "ocid1.availabilitydomain.oc1..aaaa"
          name           = "xxxx:SA-SAOPAULO-1-AD-1"
        },
        {
          compartment_id = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          id             = "ocid1.availabilitydomain.oc1..bbbb"
          name           = "xxxx:SA-SAOPAULO-1-AD-2"
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
          display_name             = "Canonical-Ubuntu-24.04-2026.10.01-0"
          freeform_tags            = {}
          id                       = "ocid1.image.oc1.sa-saopaulo-1.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          image_source_details     = []
          instance_id              = ""
          launch_mode              = "NATIVE"
          launch_options           = []
          listing_type             = "NONE"
          operating_system         = "Canonical Ubuntu"
          operating_system_version = "24.04"
          size_in_mbs              = "0"
          state                    = "AVAILABLE"
          time_created             = "2026-10-01T00:00:00Z"
        },
        {
          agent_features           = []
          base_image_id            = ""
          billable_size_in_gbs     = "0"
          compartment_id           = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          create_image_allowed     = false
          defined_tags             = {}
          display_name             = "Canonical-Ubuntu-24.04-Minimal-aarch64-2026.11.01-0"
          freeform_tags            = {}
          id                       = "ocid1.image.oc1.sa-saopaulo-1.bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          image_source_details     = []
          instance_id              = ""
          launch_mode              = "NATIVE"
          launch_options           = []
          listing_type             = "NONE"
          operating_system         = "Canonical Ubuntu"
          operating_system_version = "24.04"
          size_in_mbs              = "0"
          state                    = "AVAILABLE"
          time_created             = "2026-11-01T00:00:00Z"
        },
        {
          agent_features           = []
          base_image_id            = ""
          billable_size_in_gbs     = "0"
          compartment_id           = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          create_image_allowed     = false
          defined_tags             = {}
          display_name             = "Canonical-Ubuntu-24.04-aarch64-2026.07.01-0"
          freeform_tags            = {}
          id                       = "ocid1.image.oc1.sa-saopaulo-1.cccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
          image_source_details     = []
          instance_id              = ""
          launch_mode              = "NATIVE"
          launch_options           = []
          listing_type             = "NONE"
          operating_system         = "Canonical Ubuntu"
          operating_system_version = "24.04"
          size_in_mbs              = "0"
          state                    = "AVAILABLE"
          time_created             = "2026-07-01T00:00:00Z"
        },
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
  oci_config_profile               = "DEFAULT"
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

run "plano_conservador" {
  command = plan

  assert {
    condition     = oci_core_instance.homelab.shape == "VM.Standard.A1.Flex"
    error_message = "A shape planejada nao e VM.Standard.A1.Flex."
  }

  assert {
    condition     = oci_core_instance.homelab.shape_config[0].ocpus == 2
    error_message = "O plano nao fixou 2 OCPUs."
  }

  assert {
    condition     = oci_core_instance.homelab.shape_config[0].memory_in_gbs == 12
    error_message = "O plano nao fixou 12 GB."
  }

  assert {
    condition     = tonumber(oci_core_instance.homelab.source_details[0].boot_volume_size_in_gbs) == 50
    error_message = "O boot volume nao ficou em 50 GB."
  }

  assert {
    condition     = tonumber(oci_core_instance.homelab.source_details[0].boot_volume_vpus_per_gb) == 10
    error_message = "O boot volume nao ficou em 10 VPU/GB."
  }

  assert {
    condition     = oci_core_instance.homelab.source_details[0].source_id == "ocid1.image.oc1.sa-saopaulo-1.dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    error_message = "A consulta nao escolheu a Ubuntu 24.04 aarch64 mais recente, ou aceitou Minimal/amd64."
  }

  assert {
    condition = (
      oci_core_instance.homelab.create_vnic_details[0].assign_public_ip == true ||
      oci_core_instance.homelab.create_vnic_details[0].assign_public_ip == "true"
    )
    error_message = "O IPv4 efemero nao foi solicitado."
  }

  assert {
    condition = (
      oci_core_instance.homelab.create_vnic_details[0].assign_ipv6ip == false ||
      oci_core_instance.homelab.create_vnic_details[0].assign_ipv6ip == "false"
    )
    error_message = "IPv6 nao deve ser atribuido."
  }

  assert {
    condition     = oci_core_instance.homelab.metadata.ssh_authorized_keys == var.ssh_public_key
    error_message = "A metadata da instancia nao contem somente a chave publica informada."
  }

  assert {
    condition     = oci_core_vcn.this.is_ipv6enabled == false
    error_message = "A VCN nao deve habilitar IPv6."
  }

  assert {
    condition     = oci_core_internet_gateway.this.enabled == true
    error_message = "O internet gateway precisa existir para o IPv4 efemero."
  }

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.homelab.ingress_security_rules :
      rule.source != "0.0.0.0/0" && rule.source != "::/0"
    ])
    error_message = "Ha ingresso vindo de toda a internet."
  }

  assert {
    condition = length([
      for rule in oci_core_security_list.homelab.ingress_security_rules : rule
      if rule.protocol == "6"
    ]) == 1
    error_message = "Deve haver exatamente uma regra TCP de ingresso."
  }

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.homelab.ingress_security_rules :
      rule.protocol != "6" || (
        rule.source == "8.8.8.8/32" &&
        rule.tcp_options[0].min == 22 &&
        rule.tcp_options[0].max == 22
      )
    ])
    error_message = "O unico ingresso TCP precisa ser a porta 22 do CIDR administrativo."
  }

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.homelab.ingress_security_rules :
      rule.protocol != "6" || (
        rule.tcp_options[0].min != 6443 &&
        rule.tcp_options[0].min != 10250 &&
        (rule.tcp_options[0].min < 30000 || rule.tcp_options[0].min > 32767)
      )
    ])
    error_message = "O ingresso nao pode publicar API, kubelet ou NodePort."
  }

  assert {
    condition = (
      oci_core_default_security_list.locked.ingress_security_rules == null ||
      length(oci_core_default_security_list.locked.ingress_security_rules) == 0
    )
    error_message = "A security list padrao da VCN precisa ficar sem ingresso."
  }
}

run "aceita_admin_slash_24" {
  command = plan

  variables {
    admin_cidr = "8.8.8.0/24"
  }

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.homelab.ingress_security_rules :
      rule.protocol != "6" || rule.source == "8.8.8.0/24"
    ])
    error_message = "Um /24 publico explicito deveria ser a origem do SSH."
  }
}

run "aceita_imagem_explicita_da_mesma_regiao" {
  command = plan

  variables {
    image_id = "ocid1.image.oc1.sa-saopaulo-1.eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
  }

  assert {
    condition     = oci_core_instance.homelab.source_details[0].source_id == "ocid1.image.oc1.sa-saopaulo-1.eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    error_message = "O OCID explicito da mesma regiao nao foi usado."
  }
}

run "aceita_uma_ocpu_com_memoria_dentro_do_teto" {
  command = plan

  variables {
    ocpus     = 1
    memory_gb = 6
  }

  assert {
    condition     = oci_core_instance.homelab.shape_config[0].ocpus == 1 && oci_core_instance.homelab.shape_config[0].memory_in_gbs == 6
    error_message = "Uma instancia menor, ainda dentro de 2 OCPU e 12 GB, deveria passar."
  }
}

run "aceita_ocid_de_compartment_filho" {
  command = plan

  variables {
    compartment_ocid = "ocid1.compartment.oc1..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }

  assert {
    condition = (
      oci_core_instance.homelab.compartment_id == "ocid1.compartment.oc1..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" &&
      oci_core_vcn.this.compartment_id == "ocid1.compartment.oc1..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    error_message = "Um OCID de compartment filho deveria ser aceito."
  }
}

run "aceita_ocid_do_compartment_raiz" {
  command = plan

  variables {
    compartment_ocid = "ocid1.tenancy.oc1..cccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  }

  assert {
    condition = (
      oci_core_instance.homelab.compartment_id == "ocid1.tenancy.oc1..cccccccccccccccccccccccccccccccccccccccccccccccccccccccc" &&
      oci_core_vcn.this.compartment_id == "ocid1.tenancy.oc1..cccccccccccccccccccccccccccccccccccccccccccccccccccccccc" &&
      oci_core_subnet.public.compartment_id == "ocid1.tenancy.oc1..cccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    )
    error_message = "O OCID da tenancy, que identifica o compartment raiz, deveria ser aceito."
  }
}

run "aceita_segunda_chave_sem_abrir_rede" {
  command = plan

  variables {
    additional_ssh_public_keys = [
      {
        label      = "automation"
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDmFkZS1hdXRvbWF0aW9uLWtleS1tYXRlcmlhbA== automation-test"
      }
    ]
  }

  assert {
    condition = oci_core_instance.homelab.metadata.ssh_authorized_keys == join("\n", [
      var.ssh_public_key,
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDmFkZS1hdXRvbWF0aW9uLWtleS1tYXRlcmlhbA== automation-test",
    ])
    error_message = "As duas chaves publicas nao ficaram em linhas separadas."
  }

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.homelab.ingress_security_rules :
      rule.protocol != "6" || (
        rule.source == "8.8.8.8/32" &&
        rule.tcp_options[0].min == 22 &&
        rule.tcp_options[0].max == 22
      )
      ]) && length([
      for rule in oci_core_security_list.homelab.ingress_security_rules : rule
      if rule.protocol == "6"
    ]) == 1
    error_message = "A segunda chave nao pode criar outra origem de SSH."
  }
}
