resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  display_name   = "${var.name}-vcn"
  dns_label      = var.name
  cidr_blocks    = [local.vcn_cidr]
  is_ipv6enabled = false
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name}-igw"
  enabled        = true
  freeform_tags  = local.tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name}-public"
  freeform_tags  = local.tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
    description       = "Saida para a internet pelo internet gateway. Nao ha NAT gateway."
  }
}

resource "oci_core_security_list" "homelab" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name}-ssh"
  freeform_tags  = local.tags

  ingress_security_rules {
    protocol    = "6"
    source      = var.admin_cidr
    source_type = "CIDR_BLOCK"
    stateless   = false
    description = "SSH apenas do CIDR administrativo explicito."

    tcp_options {
      min = 22
      max = 22
    }
  }

  egress_security_rules {
    protocol         = "6"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
    description      = "HTTPS de saida para atualizacao e, se habilitado depois, download do k3s."

    tcp_options {
      min = 443
      max = 443
    }
  }

  egress_security_rules {
    protocol         = "6"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
    description      = "HTTP de saida para espelhos e redirecionamentos de pacotes."

    tcp_options {
      min = 80
      max = 80
    }
  }

  egress_security_rules {
    protocol         = "17"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
    description      = "DNS de saida."

    udp_options {
      min = 53
      max = 53
    }
  }

  egress_security_rules {
    protocol         = "6"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
    description      = "DNS de saida sobre TCP."

    tcp_options {
      min = 53
      max = 53
    }
  }

  egress_security_rules {
    protocol         = "17"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
    description      = "NTP de saida."

    udp_options {
      min = 123
      max = 123
    }
  }
}

# A security list padrao criada com a VCN abre SSH para 0.0.0.0/0.
# Ela fica sem regras e a subnet nao a utiliza.
resource "oci_core_default_security_list" "locked" {
  manage_default_resource_id = oci_core_vcn.this.default_security_list_id
  display_name               = "${var.name}-default-locked"
  freeform_tags              = local.tags
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.this.id
  display_name               = "${var.name}-public"
  dns_label                  = "pub"
  cidr_block                 = local.subnet_cidr
  prohibit_public_ip_on_vnic = false
  prohibit_internet_ingress  = false
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.homelab.id]
  freeform_tags              = local.tags
}
