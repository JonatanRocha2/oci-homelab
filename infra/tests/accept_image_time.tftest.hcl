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
          display_name             = "Canonical-Ubuntu-24.04-aarch64-2026.08.25-0"
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
          time_created             = "2026-08-27 14:38:56.936 +0000 UTC"
        },
        {
          agent_features           = []
          base_image_id            = ""
          billable_size_in_gbs     = "0"
          compartment_id           = "ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          create_image_allowed     = false
          defined_tags             = {}
          display_name             = "Canonical-Ubuntu-24.04-aarch64-2026.10.27-0"
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
          time_created             = "2026-10-30 19:53:14.707 +0000 UTC"
        }
      ]
    }
  }
}

variables {
  compartment_ocid                 = "ocid1.tenancy.oc1..cccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
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

run "escolhe_a_imagem_mais_nova_com_horario_do_provider" {
  command = plan

  assert {
    condition = (
      oci_core_instance.homelab.source_details[0].source_id == "ocid1.image.oc1.sa-saopaulo-1.dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" &&
      output.image_name == "Canonical-Ubuntu-24.04-aarch64-2026.10.27-0"
    )
    error_message = "O horario com espacos do provider nao pode ser confundido com o OCID da imagem."
  }
}
