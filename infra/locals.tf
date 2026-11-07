locals {
  tags = {
    project    = "oci-homelab"
    managed-by = "opentofu"
  }

  vcn_cidr    = "10.0.0.0/16"
  subnet_cidr = "10.0.1.0/24"

  looked_up_images = var.image_id == null ? [
    for image in data.oci_core_images.ubuntu_arm[0].images : image
    if strcontains(lower(image.display_name), "aarch64") && !strcontains(lower(image.display_name), "minimal")
  ] : []

  looked_up_newest_first = var.image_id == null ? reverse(sort([
    for image in local.looked_up_images : "${image.time_created} ${image.id}"
  ])) : []

  selected_image_id = (
    var.image_id != null ? var.image_id : (
      length(local.looked_up_newest_first) > 0 ? split(" ", local.looked_up_newest_first[0])[1] : null
    )
  )

  selected_image_name = (
    var.image_id != null || local.selected_image_id == null ? null : one([
      for image in local.looked_up_images : image.display_name
      if image.id == local.selected_image_id
    ])
  )

  availability_domain_names = [
    for ad in data.oci_identity_availability_domains.available.availability_domains : ad.name
  ]
}
