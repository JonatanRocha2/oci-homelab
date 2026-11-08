variable "compartment_ocid" {
  type        = string
  description = "OCID do compartment onde a VCN e a instancia serao criadas. Nao crie o compartment por este codigo."

  validation {
    condition     = can(regex("^ocid1\\.compartment\\.oc1\\.\\.[A-Za-z0-9._-]+$", var.compartment_ocid))
    error_message = "compartment_ocid precisa ser um OCID de compartment no formato ocid1.compartment.oc1..<unico>."
  }
}

variable "region" {
  type        = string
  description = "Regiao da infraestrutura. O padrao e sa-saopaulo-1, mas ela so pode ser usada se for a home region da tenancy."
  default     = "sa-saopaulo-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z0-9-]+-[0-9]+$", var.region))
    error_message = "region precisa ser um identificador de regiao da OCI, por exemplo sa-saopaulo-1."
  }
}

variable "home_region" {
  type        = string
  description = "Home region exata mostrada nos detalhes da tenancy na console. Compute e Block Volume Always Free so valem nessa regiao."

  validation {
    condition     = var.home_region == var.region
    error_message = "home_region precisa ser identica a region. Always Free de compute e block volume nao segue a regiao escolhida no codigo; ele segue a home region da tenancy."
  }
}

variable "home_region_confirmed" {
  type        = bool
  description = "Defina true somente depois de comparar home_region com a home region exibida na console. O selo Always Free-eligible da shape nao confirma a home region."
  default     = false

  validation {
    condition     = var.home_region_confirmed
    error_message = "home_region_confirmed precisa ser true depois da conferencia manual da home region. Sem essa confirmacao o plano para."
  }
}

variable "manual_limits_checked" {
  type        = bool
  description = "Defina true somente depois de olhar Limits, Quotas and Usage na home region e confirmar saldo para 2 OCPU, 12 GB e 50 GB. Isso nao prova capacidade fisica da regiao."
  default     = false

  validation {
    condition     = var.manual_limits_checked
    error_message = "manual_limits_checked precisa ser true depois da conferencia manual de cota restante. Capacidade de host continua nao verificada e pode falhar depois, num apply separado."
  }
}

variable "public_ipv4_pricing_acknowledged" {
  type        = bool
  description = "Defina true somente depois de reler a lista de precos vigente para IPv4 efemero e transferencia de saida. Este fundamento nao cria IPv4 reservado."
  default     = false

  validation {
    condition     = var.public_ipv4_pricing_acknowledged
    error_message = "public_ipv4_pricing_acknowledged precisa ser true. O plano nao assume que o IPv4 publico efemero permaneca gratuito."
  }
}

variable "availability_domain" {
  type        = string
  description = "Nome exato do availability domain, incluindo o prefixo da tenancy, por exemplo xxxx:SA-SAOPAULO-1-AD-1."

  validation {
    condition     = can(regex("^[A-Za-z0-9:_-]{8,255}$", var.availability_domain))
    error_message = "availability_domain precisa ser o nome exato retornado pela OCI, sem espacos."
  }
}

variable "oci_config_profile" {
  type        = string
  description = "Perfil dentro de ~/.oci/config. Nao e um segredo; a chave permanece fora do repositorio."
  default     = "DEFAULT"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]{1,64}$", var.oci_config_profile))
    error_message = "oci_config_profile precisa ser um nome simples de perfil."
  }
}

variable "name" {
  type        = string
  description = "Prefixo curto usado em nomes e no hostname da instancia."
  default     = "homelab"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.name))
    error_message = "name precisa ter de 2 a 15 caracteres, comecar com letra e usar apenas minusculas, numeros e hifen."
  }
}

variable "instance_shape" {
  type        = string
  description = "Shape unica aceita por este fundamento."
  default     = "VM.Standard.A1.Flex"

  validation {
    condition     = var.instance_shape == "VM.Standard.A1.Flex"
    error_message = "A unica shape aceita e VM.Standard.A1.Flex. Outras shapes podem ser cobradas."
  }
}

variable "ocpus" {
  type        = number
  description = "OCPUs da unica instancia. O teto conservador e 2, o total Always Free documentado para A1 em 7 de novembro de 2026."
  default     = 2

  validation {
    condition     = var.ocpus == 1 || var.ocpus == 2
    error_message = "ocpus precisa ser 1 ou 2. O total Always Free vigente usado aqui e 2 OCPUs, nao o antigo limite de 4."
  }
}

variable "memory_gb" {
  type        = number
  description = "Memoria em GB inteiros. O teto conservador e 12 GB no total da tenancy para A1."
  default     = 12

  validation {
    condition = (
      var.memory_gb == floor(var.memory_gb) &&
      var.memory_gb >= var.ocpus &&
      var.memory_gb <= 12 &&
      var.memory_gb <= var.ocpus * 64
    )
    error_message = "memory_gb precisa ser inteiro, caber em 1 GB por OCPU ate 64 GB por OCPU, e nao passar de 12 GB. O antigo teto de 24 GB nao e aceito."
  }
}

variable "boot_volume_gb" {
  type        = number
  description = "Tamanho do unico disco, o boot volume. Fixo em 50 GB para ficar dentro do conjunto de 200 GB e nao consumir o saldo sozinho."
  default     = 50

  validation {
    condition     = var.boot_volume_gb == 50
    error_message = "boot_volume_gb precisa permanecer em 50. Este fundamento nao cria volume extra nem backup. Cinquenta GB nao enxergam discos que ja existam na tenancy."
  }
}

variable "boot_volume_vpus_per_gb" {
  type        = number
  description = "Desempenho do boot volume. Boot volume nao aceita 0 VPU; 10 e o nivel Balanced padrao. Valores maiores sao recusados."
  default     = 10

  validation {
    condition     = var.boot_volume_vpus_per_gb == 10
    error_message = "boot_volume_vpus_per_gb precisa ser 10, o nivel Balanced. Nao aumente o desempenho por este fundamento."
  }
}

variable "assign_ephemeral_public_ipv4" {
  type        = bool
  description = "A instancia recebe um unico IPv4 publico efemero. IPv4 reservado nao e criado."
  default     = true

  validation {
    condition     = var.assign_ephemeral_public_ipv4
    error_message = "assign_ephemeral_public_ipv4 precisa ser true. Sem o IPv4 efemero esta base nao tem caminho de SSH e ainda assim consumiria cota."
  }
}

variable "admin_cidr" {
  type        = string
  description = "CIDR IPv4 publico de origem do SSH, em geral o /32 atual do administrador. 0.0.0.0/0 e redes privadas sao recusados."

  validation {
    condition = (
      can(regex("^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])/(2[4-9]|3[0-2])$", var.admin_cidr)) &&
      try(cidrhost(var.admin_cidr, 0), null) != null &&
      var.admin_cidr == format("%s/%s", try(cidrhost(var.admin_cidr, 0), ""), try(split("/", var.admin_cidr)[1], "")) &&
      tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "-1")) >= 1 &&
      tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "255")) <= 223 &&
      tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "10")) != 10 &&
      tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "127")) != 127 &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 100 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) >= 64 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) <= 127
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 169 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 254
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 172 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) >= 16 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) <= 31
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 192 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 168
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 192 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 0 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[2], "0")) <= 2
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 198 &&
        (
          tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 18 ||
          tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 19 ||
          (
            tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 51 &&
            tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[2], "0")) == 100
          )
        )
      ) &&
      !(
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[0], "0")) == 203 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[1], "0")) == 0 &&
        tonumber(try(split(".", cidrhost(var.admin_cidr, 0))[2], "0")) == 113
      )
    )
    error_message = "admin_cidr precisa ser um CIDR IPv4 publico canonico, /24 ou menor. Sao recusados 0.0.0.0/0, redes privadas, loopback, link-local, CGNAT, multicast e as redes de documentacao 192.0.2.0/24, 198.51.100.0/24 e 203.0.113.0/24."
  }
}

variable "ssh_public_key" {
  type        = string
  description = "Chave publica OpenSSH principal. Chaves adicionais ficam em additional_ssh_public_keys e saem sem alterar esta."

  validation {
    condition = (
      can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) AAAA[0-9A-Za-z+/]+=*( [^\r\n]+)?$", var.ssh_public_key)) &&
      !strcontains(var.ssh_public_key, "PRIVATE") &&
      !strcontains(var.ssh_public_key, "BEGIN ") &&
      length(var.ssh_public_key) <= 4096
    )
    error_message = "ssh_public_key precisa ser uma unica chave publica OpenSSH em uma linha. Chave privada e material BEGIN sao recusados. Este repositorio nao gera chaves."
  }
}

variable "additional_ssh_public_keys" {
  type = list(object({
    label      = string
    public_key = string
  }))
  description = "Chaves publicas adicionais, cada uma removivel pelo proprio label. Nao acrescentam origem de rede: o SSH continua somente em admin_cidr."
  default     = []

  validation {
    condition = (
      length(var.additional_ssh_public_keys) <= 3 &&
      length(distinct([for key in var.additional_ssh_public_keys : key.label])) == length(var.additional_ssh_public_keys) &&
      length(distinct([
        for key in var.additional_ssh_public_keys : try(split(" ", key.public_key)[1], "")
      ])) == length(var.additional_ssh_public_keys) &&
      alltrue([
        for key in var.additional_ssh_public_keys :
        can(regex("^[a-z0-9][a-z0-9-]{0,40}$", key.label)) &&
        can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) AAAA[0-9A-Za-z+/]+=*( [^\r\n]+)?$", key.public_key)) &&
        !strcontains(key.public_key, "PRIVATE") &&
        !strcontains(key.public_key, "BEGIN ") &&
        length(key.public_key) <= 4096 &&
        try(split(" ", key.public_key)[1], "") != try(split(" ", var.ssh_public_key)[1], "")
      ])
    )
    error_message = "additional_ssh_public_keys aceita no maximo tres chaves publicas OpenSSH, com labels unicos. Chave privada, material BEGIN e chave repetida sao recusados. A lista nao abre outra origem de SSH."
  }
}

variable "image_id" {
  type        = string
  description = "OCID opcional de uma imagem ja conferida na regiao. Deixe null para selecionar a Canonical Ubuntu 24.04 aarch64 mais recente compativel com VM.Standard.A1.Flex. Nao use Ubuntu Minimal em ARM."
  default     = null
  nullable    = true

  validation {
    condition = (
      var.image_id == null ||
      (
        can(regex("^ocid1\\.image\\.oc1\\.[A-Za-z0-9-]+\\.[A-Za-z0-9._-]+$", var.image_id)) &&
        strcontains(var.image_id, ".${var.region}.")
      )
    )
    error_message = "image_id, quando informado, precisa ser um OCID de imagem da mesma region. Um OCID de outra regiao e recusado. Se a regiao usar um codigo curto no OCID, deixe image_id nulo e use a consulta."
  }
}
