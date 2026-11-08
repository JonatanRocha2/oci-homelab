# oci-homelab

Fundamento de um homelab com uma unica VM Ampere A1 na Oracle Cloud Infrastructure. O OpenTofu descreve a rede e a instancia. O Ansible endurece o Ubuntu depois, e so instala o k3s se isso for ligado de proposito.

Nada neste repositorio cria recurso na OCI. Nao ha `apply`, `destroy`, chave, politica IAM nem estado remoto.

## Arquitetura

Uma VCN nova, isolada, com o minimo para uma instancia alcancavel por SSH:

```text
administrador (CIDR IPv4 explicito)
        |  TCP 22
        v
internet gateway
        |
route table 0.0.0.0/0
        |
subnet publica regional 10.0.1.0/24
        |
VM.Standard.A1.Flex
  2 OCPU, 12 GB, boot 50 GB
  Ubuntu 24.04 aarch64, quando a consulta a encontrar
  um IPv4 publico efemero
```

A VCN usa `10.0.0.0/16`. A subnet e regional, entao o availability domain escolhe so a instancia. A security list da subnet tem uma unica entrada: TCP 22 vindo de `admin_cidr`. A security list padrao da VCN, que a OCI cria com SSH aberto para `0.0.0.0/0`, fica sem regras e nao e ligada a subnet.

Nao ha NAT gateway, IP publico reservado, balanceador, volume extra, backup, IPv6, NSG nem Kubernetes publico. A saida passa pelo internet gateway e so libera TCP 80 e 443, DNS 53 e NTP 123. O retorno entra porque a security list e stateful.

O k3s, se for habilitado depois no Ansible, escuta na VNIC privada. A API, o kubelet e a faixa NodePort nao entram na security list. Traefik e ServiceLB ficam desligados. Nao ha dashboard.

## O que foi conferido em 7 de novembro de 2026

Fontes lidas nessa data:

- [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Cloud Infrastructure Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Platform Images](https://docs.oracle.com/en-us/iaas/Content/Compute/References/images.htm)
- [Find Ubuntu images on Oracle Cloud](https://ubuntu.com/docs/oracle/oracle-how-to/find-ubuntu-images/)
- [Public IP Addresses](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm)
- [Block Volume Performance](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeperformance.htm)
- [Virtual Cloud Network FAQ](https://www.oracle.com/cloud/networking/virtual-cloud-network/faq/), secao Billing
- [Virtual Cloud Network Pricing](https://www.oracle.com/cloud/networking/virtual-cloud-network/pricing/)
- Lista global de precos com data de 8 de outubro de 2026, ligada em [Cloud Price List](https://www.oracle.com/cloud/price-list/)

A pagina Always Free, nessa leitura, diz:

- Ampere A1 (`VM.Standard.A1.Flex`): as primeiras 1.500 horas de OCPU e 9.000 horas de GB por mes. Para tenancies Always Free isso equivale a 2 OCPUs e 12 GB no total, numa instancia ou em ate duas.
- As instancias Always Free de compute precisam ser criadas na home region.
- Block Volume: 200 GB somando boot volume e block volume, na home region, e cinco backups no total. Este fundamento cria um boot volume de 50 GB e nenhum backup.
- A mesma pagina diz, em pontos diferentes, minimo de boot de 47 GB e minimo de 50 GB. O valor usado aqui e 50 GB, que atende a frase mais estrita e o padrao descrito pela Oracle.
- Imagens citadas para A1 incluem Ubuntu. A pagina de platform images diz que Ubuntu 24.04 suporta x86 e ARM, e que em ARM se usa a imagem Ubuntu, nao a Minimal.
- Se faltar capacidade, a OCI devolve "out of host capacity". Isso e temporario e nao e resolvido por este codigo.
- Instancia Always Free ociosa pode ser reclamada. A pagina descreve 7 dias com CPU, rede e, no A1, memoria abaixo de 20% no percentil 95.
- Tenancies Free Tier que nao sao pagas e nao tem credito de trial podem ter ate 2 VCNs. Esta base cria uma VCN nova.

A pagina Free Tier separa as duas ofertas:

- Free Trial: US$ 300 em creditos, validos por ate 30 dias, gastaveis em servicos elegiveis.
- Always Free: ofertas que nao expiram, so na home region.
- Credito de trial, ou uma VM que tenha rodado enquanto o credito existia, nao prova que o formato continua de graca depois.
- A propria pagina pede que, antes do fim do trial, o total de A1 da tenancy nao passe de 2 OCPUs e 12 GB. Acima disso as instancias A1 existentes sao desligadas e apagadas depois de 30 dias, a menos que a conta seja convertida em paga. Recurso pago criado com credito e reclamado se a conta nao for convertida.

A lista de precos de 8 de outubro de 2026 ainda descreve o A1 como as primeiras 3.000 horas de OCPU e 18.000 horas de GB. Este fundamento nao usa esse numero antigo. A pagina Always Free e o aviso do trial, ambos lidos em 7 de novembro de 2026, dizem 2 OCPUs e 12 GB. O codigo recusa 4 OCPUs e 24 GB.

## Estas checagens nao garantem custo zero

Os limites do OpenTofu olham so para o que este codigo pretende criar. Eles nao enxergam o resto da tenancy. Continua possivel haver custo por causa de:

- outras instancias A1, volumes, backups ou saida de dados que ja existam
- saida de internet acima de 10 TB no mes, que a pagina de preco de VCN lista como a franquia
- o metro de desempenho do Block Volume, separado do metro de armazenamento
- divergencia entre a pagina Always Free e a lista de precos, se a cobranca seguir o outro texto
- imposto, upgrade de conta, ou recurso criado fora deste diretorio
- um apply futuro que alguem altere antes de aprovar

O selo Always Free-eligible visto na console para a shape A1 nao foi reconsultado por este repositorio. Home region, cota restante e capacidade regional tambem nao foram consultadas. Nao ha chamada de API aqui.

## IPv4 publico

A instancia pede um IPv4 efemero na VNIC primaria. Nao existe recurso de IP reservado. A FAQ de VCN diz que criar e usar uma VCN nao tem tarifa propria, e que transferencia e outros servicos seguem a tabela publicada. A pagina de preco de VCN consultada nao cobra o trafego dentro da regiao e inclui 10 TB/mes de saida para a internet. Na lista de 8 de outubro de 2026 nao apareceu um SKU horario separado de IPv4 efemero. Isso nao e uma garantia: a tabela pode mudar, e o plano exige `public_ipv4_pricing_acknowledged = true` so depois de uma nova leitura.

NAT gateway e balanceador ficam de fora. O caminho de SSH e a subnet publica mais o internet gateway.

O boot volume fica em 10 VPU/GB, o nivel Balanced. A documentacao de desempenho diz que boot volume nao oferece o nivel Lower Cost de 0 VPU, e que VPU e um metro comprado em incrementos de 10. Nao aumente esse valor. Confira o Cost Analysis depois de qualquer apply futuro. Cinquenta gigabytes a 10 VPU/GB podem ou nao entrar na franquia, e este repositorio nao consegue provar isso sem a conta.

## Conferencias manuais antes de qualquer plano real

1. Na console, abra os detalhes da tenancy e copie a home region. Ela tem de ser o valor de `region` e de `home_region`. `sa-saopaulo-1` e so o padrao do codigo.
2. Em Governance & Administration, abra Limits, Quotas and Usage, filtre a home region e confira o saldo de OCPU A1, memoria A1 e armazenamento de block volume. Este stack pede 2 OCPUs, 12 GB e 50 GB, alem de uma VCN se a conta ainda estiver no teto de duas.
3. Capacidade de host nao aparece como saldo. "Out of host capacity" so surge numa tentativa de criacao. Este repositorio nao faz essa tentativa. Trocar de availability domain e uma decisao manual posterior, nao um loop da CI.
4. No Cost Analysis e na lista de precos vigente, confira IPv4 efemero, 10 VPU/GB e a franquia de 10 TB de saida para o tipo da sua conta.
5. Se ainda houver credito de trial, trate esse credito como promocao. O alvo daqui e o teto Always Free de 2 OCPUs e 12 GB, nao o que o credito consegue ligar hoje.

So depois disso os tres booleanos podem ser `true`.

## Imagem

Nao ha OCID de imagem gravado no codigo. Imagem de plataforma muda por regiao e por mes. No plano real, `oci_core_images` filtra `Canonical Ubuntu`, versao `24.04`, shape `VM.Standard.A1.Flex` e estado `AVAILABLE`, ordenado por data. O codigo fica com a mais nova cujo nome contem `aarch64` e nao contem `Minimal`. Se a lista vier vazia, o plano para. Nao ha imagem de reserva embutida.

`image_id` existe para um OCID que voce ja tenha visto na mesma regiao. Um OCID de outra regiao e recusado. Na duvida, deixe `null`.

## Variaveis que o plano exige

| Variavel | Funcao |
| --- | --- |
| `compartment_ocid` | Compartment existente. O raiz e o OCID da tenancy, `ocid1.tenancy.oc1..<unico>`. Um filho e `ocid1.compartment.oc1..<unico>`. O codigo nao cria compartment. |
| `region` | Padrao `sa-saopaulo-1`. Tem de ser a home region. |
| `home_region` | Texto exato da console. Precisa ser igual a `region`. |
| `home_region_confirmed` | `true` so depois do passo 1. Padrao `false`. |
| `manual_limits_checked` | `true` so depois do passo 2. Nao afirma capacidade. Padrao `false`. |
| `public_ipv4_pricing_acknowledged` | `true` so depois do passo 4. Padrao `false`. |
| `availability_domain` | Nome completo, com o prefixo da tenancy. |
| `admin_cidr` | Unica origem do SSH. IPv4 publico, canonico, `/24` ou menor. |
| `ssh_public_key` | Chave publica OpenSSH principal. Chave privada e recusada. |
| `additional_ssh_public_keys` | Outras chaves publicas, cada uma com `label`. Remover o item revoga so essa chave. Nao abre outra origem. |
| `image_id` | Opcional. `null` usa a consulta. |

`ssh_public_key` e os itens de `additional_ssh_public_keys` entram em linhas separadas na metadata `ssh_authorized_keys`, para a conta `ubuntu`. A security list permanece com uma regra de ingresso: TCP 22 vindo de `admin_cidr`. Uma chave de automacao nao conecta enquanto o `/32` de origem dela nao for aprovado e configurado nesse unico CIDR. Sem esse `/32`, a chave pode estar na instancia e ainda assim nao atravessa a rede.

Os tetos fixos sao shape `VM.Standard.A1.Flex`, 1 ou 2 OCPUs, memoria inteira entre 1 GB por OCPU e 12 GB, boot de 50 GB e 10 VPU/GB. `0.0.0.0/0`, rede privada, loopback, link-local, CGNAT, multicast e as redes de documentacao `192.0.2.0/24`, `198.51.100.0/24` e `203.0.113.0/24` nao servem como origem de SSH. O exemplo usa `203.0.113.10/32` de proposito, para falhar ate ser trocado.

## Autenticacao da API, sem criar credencial

O provider le o perfil de `~/.oci/config` no seu computador. O codigo nao recebe user OCID, tenancy OCID, fingerprint nem caminho de chave. `oci_config_profile` so escolhe o nome do perfil, em geral `DEFAULT`.

Voce cria a chave e a policy fora deste repositorio, na console, se ainda nao existirem:

1. Identity, no seu usuario, em API keys, adicione uma chave publica. Guarde a chave privada so na sua maquina, modo `0600`, fora do Git. A console mostra o fingerprint e um exemplo de configuracao.
2. Grave `~/.oci/config` com `user`, `fingerprint`, `tenancy`, `region` e `key_file`. Nao copie esse arquivo para ca.
3. Uma policy no compartment, criada por um administrador da tenancy, no minimo:

```text
Allow group <grupo> to manage instance-family in compartment <compartment>
Allow group <grupo> to manage volume-family in compartment <compartment>
Allow group <grupo> to manage virtual-network-family in compartment <compartment>
Allow group <grupo> to read instance-images in compartment <compartment>
Allow group <grupo> to inspect compartments in tenancy
```

`manage virtual-network-family` cobre VCN, subnet, internet gateway, route table e security list. E amplo dentro de um compartment e nao deve ser aplicado na tenancy inteira se der para evitar. Este repositorio nao cria grupo, usuario, policy nem chave.

A consulta de availability domain e a listagem de imagens de plataforma usam o mesmo compartment. A listagem de imagens de plataforma aceita o OCID do compartment em que voce tem `read instance-images`.

## Estado

O backend configurado no codigo e S3 compativel, com `use_lockfile`, trava nativa do OpenTofu e sem tabela extra. O bucket, a regiao e o endpoint nao entram no Git. Eles ficam em `infra/backend.hcl`, copiado de `infra/backend.hcl.example`, ou no segredo `HOMELAB_BACKEND_CONFIG`. O arquivo de exemplo usa `SUBSTITUA` de proposito.

O estado guarda OCID e o IP publico. Um bucket novo, vazio, faz o proximo plano querer criar tudo de novo. O workflow recusa estado sem recursos, a menos que `acknowledge_empty_state` esteja marcado, e recusa essa marca quando o estado ja tem recursos. Se a lineage ou o serial mudarem entre o plano e o apply, o apply para.

Este codigo nao cria bucket, chave nem policy. A pagina publica de Always Free lista 20 GB de Object Storage e 50.000 requisicoes por mes; isso nao foi tratado como autorizacao para criar o bucket, nem como garantia de preco na sua tenancy. O bucket, se voce o criar, precisa ser privado, sem acesso publico e sem pre-authenticated request para o objeto de estado.

Nao suba estado, plano ou chave para o Git. O artifact do plano e cifrado. Artifact de repositorio publico pode ser lido por qualquer pessoa; por isso o arquivo publicado e so `homelab-plan.enc`.

## Plano e apply

O caminho suportado e `.github/workflows/homelab.yml`, disparado a mao em `main`. Push e pull request nao planejam e nao aplicam. Nao ha workflow de destroy.

`operation=plan` usa o ambiente `homelab-plan`, troca um JWT efemero do GitHub por um RPST e grava o plano cifrado. O resumo publicado lista shape, tamanho e contagem de regras. Nao lista OCID, chave nem o CIDR de origem do SSH. O workflow nao define `public_ipv4_pricing_acknowledged`. Esse valor so pode vir do `HOMELAB_TFVARS` que voce gravar, e continua sendo o reconhecimento de que o preco do IPv4 efemero nao ficou provado. Nao e garantia de custo zero.

`operation=apply` usa o ambiente `homelab-apply`. O nome do ambiente, sozinho, nao segura o job. O script exige um registro `approved` desse ambiente, feito por outra pessoa, e falha se a lista vier vazia. Tambem exige que a execucao do plano tenha sido `workflow_dispatch` em `main`, com o mesmo SHA, e aplica apenas o arquivo daquele plano. Plano com delete, replace ou recurso fora da lista fechada nao segue.

A autenticacao do workflow e `OCI_AUTH=ResourcePrincipal`. A chave de API que ja existe na sua maquina nao entra no GitHub. O customer secret key do bucket tambem nao e essa chave de API.

No seu computador, o plano local ainda usa a chave de API do `~/.oci/config`. Ele precisa do mesmo backend, senao aponta para outro estado:

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl
# edite os dois; os arquivos reais sao ignorados pelo Git
tofu init -backend-config=backend.hcl
tofu plan -out=homelab.tfplan
```

Um apply local nao passa pela aprovacao nem pela conferencia do plano salvo. Nao use o apply local contra este estado.

## Ansible

O inventario de exemplo aponta para `203.0.113.10` e nao abre sessao. O inventario real fica em `ansible/inventories/local/`, ignorado pelo Git, e so deve ser escrito depois que o apply tiver mostrado o IP publico.

```yaml
all:
  hosts:
    homelab:
      ansible_host: SUBSTITUA_PELO_IP_PUBLICO
      ansible_user: ubuntu
```

A chave privada fica no agente SSH ou em `ansible_ssh_private_key_file` nesse inventario local. Nao a coloque no Git.

```bash
cd ansible
ansible-playbook -i inventories/local/hosts.yml site.yml
```

O papel `base` e idempotente: instala `unattended-upgrades` so com origem de seguranca, sem reboot automatico, e grava `/etc/ssh/sshd_config.d/00-homelab.conf`. Esse nome vem antes dos outros drop-ins, porque o sshd usa o primeiro valor que encontra. Ele desliga senha e root, exige chave publica e limita o usuario. O padrao e `ubuntu`, o usuario da imagem Canonical. Antes de recarregar o ssh, a tarefa roda `sshd -t`. Se a validacao falhar, o arquivo anterior volta e o servico nao e recarregado.

UFW nao e usado. A documentacao de imagens da OCI avisa que o UFW pode impedir o boot do Ubuntu.

### k3s opcional

`k3s_enabled` nasce `false`. Para ligar, passe a variavel de forma explicita:

```bash
ansible-playbook -i inventories/local/hosts.yml site.yml -e k3s_enabled=true
```

O papel so continua em ARM64. Ele baixa `k3s-arm64` e o `install.sh` da tag `v1.37.2+k3s1` e confere os SHA-256 gravados em `ansible/roles/k3s/defaults/main.yml`. O instalador roda com `INSTALL_K3S_SKIP_DOWNLOAD=true`, entao usa o binario ja verificado. A configuracao desliga Traefik e ServiceLB, anuncia o IP privado da VNIC e nao coloca o IP publico em `tls-san`. O kubeconfig fica em `/etc/rancher/k3s/k3s.yaml`, modo `0600`, dono root. O papel recusa qualquer copia para a maquina de controle.

Para usar o kubectl sem abrir a API, o encaminhamento local do SSH basta:

```bash
ssh -L 6443:127.0.0.1:6443 ubuntu@IP_PUBLICO
```

Se precisar do arquivo na sua maquina, copie por esse SSH, troque o endereco do servidor e guarde fora do repositorio com modo `0600`. Nao faca commit.

## O que este codigo deixa pronto

O repositorio tem o workflow, o backend parcial, a cifra do plano e os testes que recusam aprovacao vazia, estado vazio e plano trocado. Isso e codigo pronto. Nao e operacao pronta. Nenhum secret foi gravado no GitHub, nenhum ambiente foi criado e nenhum recurso da OCI foi pedido por este fluxo.

Para o dispatch funcionar, falta a configuracao que so voce pode fazer:

1. Confirmar se o Object Storage cabe na sua conta e, se couber, criar um bucket privado. O codigo nao o cria.
2. Criar um customer secret key so para esse bucket. Nao envie a chave de API que ja assina a CLI.
3. Criar a aplicacao confidencial do identity domain e a Identity Propagation Trust. O issuer e `https://token.actions.githubusercontent.com`, o `impersonatingResource` e `githubactions`, e a audiencia pedida pelo workflow e `oci-homelab`. As validacoes de claim sao todas obrigatorias ao mesmo tempo; as cinco que fecham este repositorio sao `repository=JonatanRocha2/oci-homelab`, `ref=refs/heads/main`, `ref_type=branch`, `aud=oci-homelab` e `job_workflow_ref=JonatanRocha2/oci-homelab/.github/workflows/homelab.yml@refs/heads/main`.
4. Escrever a policy de IAM do resource principal no compartment que voce ja usa. O repositorio nao cria policy.
5. Criar os ambientes `homelab-plan` e `homelab-apply`. Em `homelab-apply`, marcar required reviewers e impedir autoaprovacao. Sem esse reviewer, o GitHub nao espera ninguem; o script entao falha porque a lista de aprovacao vem vazia.
6. Gravar os mesmos nomes de segredo nos dois ambientes: `OCI_IDENTITY_DOMAIN_URL`, `OCI_OAUTH_CLIENT_ID`, `OCI_OAUTH_CLIENT_SECRET`, `OCI_CUSTOMER_SECRET_KEY_ID`, `OCI_CUSTOMER_SECRET_KEY`, `HOMELAB_BACKEND_CONFIG`, `HOMELAB_TFVARS` e `HOMELAB_PLAN_PASSPHRASE`. `HOMELAB_TFVARS` e o unico lugar das confirmacoes de cota e de preco. `HOMELAB_PLAN_PASSPHRASE` cifra o plano. O backend nao leva a chave de acesso dentro do texto.
7. Proteger `main`. O `workflow_dispatch` executa o YAML que estiver em `main`, mesmo quando o apply faz checkout do SHA antigo. Sem essa protecao, uma gravacao direta em `main` pode trocar o workflow.

Pull request, inclusive de fork, continua so em `validate.yml`: `contents: read`, sem segredo, sem `id-token` e sem ambiente.

## CI

`.github/workflows/validate.yml` so tem `contents: read`. Instala o OpenTofu 1.13.9 conferindo o SHA-256, instala Ansible pelos pins de `requirements-ci.txt` e roda `scripts/ci.sh`. Isso faz a conferencia do repositorio, os testes do gate de aprovacao, `tofu fmt -check`, `tofu init -backend=false`, `tofu validate`, `tofu test` e o lint do Ansible. Nao ha segredo, plano remoto nem apply nesse workflow.

O provider `oracle/oci` 9.12.1 esta em `infra/.terraform.lock.hcl`, com hashes para Linux e macOS em amd64 e arm64.

## Testes feitos aqui

Com a maquina sem `~/.oci/config` e sem variavel de credencial OCI:

- `tofu fmt -check`
- `tofu init -backend=false`
- `tofu validate`
- `tofu test`: 42 cenarios com o provider simulado, sem API da OCI
- `ansible-lint` no perfil moderate, que passou no perfil production
- `ansible-playbook --syntax-check` no inventario de exemplo
- `scripts/check-repository.sh` e `scripts/check-pipeline.sh`, que recusam estado, tfvars privado, chave, kubeconfig, NAT, IP reservado, balanceador, volume extra, destroy, apply fora do plano salvo, aprovacao vazia e estado remoto vazio

Os cenarios do OpenTofu cobrem o plano de 2 OCPUs, 12 GB, boot de 50 GB e 10 VPU, a escolha da imagem aarch64 mais nova, a recusa de Minimal e amd64, a recusa de um availability domain que a consulta nao devolveu, e as recusas de CIDR, shape, memoria, disco, VPU, home region, confirmacoes e chave privada.

## O que nao foi testado

- `tofu plan` ou `tofu apply` contra uma tenancy
- a consulta real de imagem e de availability domain
- home region, cota restante, capacidade e Cost Analysis
- SSH, apt, reload do sshd e instalacao do k3s numa VM
- se 10 VPU/GB ou o IPv4 efemero aparecem como R$ 0 na sua fatura
- a policy IAM, porque ela nao deve ser criada por este codigo
- `workflow_dispatch`, a troca do JWT por RPST, o bucket e os ambientes do GitHub; a aprovacao foi exercitada com fixtures, nao com um ambiente real
