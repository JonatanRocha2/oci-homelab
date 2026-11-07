output "instance_id" {
  description = "OCID da instancia, preenchido apenas depois de um apply aprovado separadamente."
  value       = oci_core_instance.homelab.id
}

output "availability_domain" {
  description = "Availability domain usado pela instancia."
  value       = oci_core_instance.homelab.availability_domain
}

output "image_id" {
  description = "OCID da imagem selecionada."
  value       = local.selected_image_id
}

output "image_name" {
  description = "Nome da imagem encontrada pela consulta. Nulo quando image_id foi informado explicitamente."
  value       = local.selected_image_name
}

output "private_ip" {
  description = "IPv4 privado da VNIC primaria."
  value       = oci_core_instance.homelab.private_ip
}

output "public_ip" {
  description = "IPv4 publico efemero. Muda se a instancia for recriada. Nao e um endereco reservado."
  value       = oci_core_instance.homelab.public_ip
}

output "subnet_cidr" {
  description = "CIDR da unica subnet."
  value       = oci_core_subnet.public.cidr_block
}

output "ssh_admin_cidr" {
  description = "Origem autorizada para TCP 22."
  value       = var.admin_cidr
}
