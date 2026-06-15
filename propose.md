# Trabalho Final — Protocolo de transporte confiável sobre UDP

## Pontifícia Universidade Católica do Rio Grande do Sul
Escola Politécnica – Laboratório de Redes de Computadores

## Objetivo
Este trabalho tem como objetivo o projeto, implementação e análise de um protocolo de transporte confiável sobre UDP denominado SRTP (Simple Reliable Transport Protocol). O protocolo deve transferir arquivos de forma confiável entre dois hosts distintos em rede local, implementando mecanismos de controle de erros e fluxo.

O trabalho é dividido em:
- Parte 1: Stop-and-Wait
- Parte 2: Go-Back-N (GBN) e Selective Repeat (SR)

---

# Especificação do Protocolo RTP

## Camada de transporte subjacente
O RTP opera sobre UDP. Toda confiabilidade, controle de fluxo e ordenação são responsabilidade do próprio protocolo.

## Modelo de comunicação
O RTP é half-duplex: apenas um lado transmite dados por vez. O outro lado envia apenas ACK/NACK.

## Formato do cabeçalho

| Campo | Bits | Descrição |
|---------|------|-------------|
| SEQ | 14 | Número de sequência do pacote |
| SYN | 1 | Estabelecimento de conexão |
| FIN | 1 | Encerramento de conexão |
| ACK | 14 | Número de acknowledgement |
| ACK flag | 1 | Indica ACK válido |
| NACK | 1 | Negative acknowledgement |
| Length | 8 | Tamanho do payload ou janela proposta |
| CRC32 | 32 | Checksum CRC32 |

## Semântica do campo Length

### Durante a transferência
- Length = 255 → pacote intermediário.
- Length < 255 → último pacote do stream.
- Length = 0 → arquivo múltiplo exato de 255 bytes.

### Durante o handshake
- Representa o tamanho de janela proposto.

## Número de sequência
- Contado em pacotes.
- Inicia em 0 após handshake.
- Espaço de sequência: 14 bits (0–16383).
- Deve tratar wrap-around corretamente.

## Checksum
- Algoritmo CRC32.
- Calculado sobre cabeçalho (CRC zerado) + payload.
- Pacotes inválidos são descartados silenciosamente.

## Estabelecimento de conexão (three-way handshake)
1. Sender envia SYN.
2. Receiver responde SYN+ACK.
3. Sender envia ACK.

A janela efetiva é o menor valor proposto entre os lados.

## Encerramento (two-way)
1. Sender envia FIN.
2. Receiver responde FIN+ACK.

## Timeout e retransmissão
- Timeout fixo: 100 ms.
- Timeout dispara retransmissão.

## Modelo de portas
- Receiver escuta em P.
- Sender conecta em P.
- Após handshake, sender escuta ACK/NACK em P+1.

## Transferência bidirecional
Cada direção utiliza uma nova sessão com handshake e encerramento independentes.

---

# Parte 1 – Stop-and-Wait

## Regras
- Um pacote por vez.
- Aguarda ACK antes do próximo envio.
- Timeout de 100 ms retransmite.
- ACK para pacotes válidos.
- Pacotes inválidos descartados.
- Pacotes fora de ordem descartados.

## Testes obrigatórios

### Cenários de latência

| Cenário | Latência |
|----------|----------|
| L0 | 0 ms |
| L1 | 50 ms |
| L2 | 100 ms |
| L3 | 150 ms |

### Cenários de perda

| Cenário | Perda |
|----------|--------|
| P0 | 0% |
| P1 | 1% |
| P2 | 5% |
| P3 | 10% |
| P4 | 25% |

## Relatório – Parte 1
1. Throughput teórico máximo.
2. Análise dos cenários de latência.
3. Análise dos cenários de perda.
4. Análise do comportamento do CRC32.

---

# Parte 2 – Go-Back-N e Selective Repeat

## Seleção do modo
Exemplo:
```bash
--mode [saw|gbn|sr]
```

## Go-Back-N
- Janela de N pacotes.
- Receiver aceita apenas ordem correta.
- Timeout/NACK retransmite em lote.
- ACK cumulativo.
- Usa NACK para pacote esperado.

## Selective Repeat
- Janela de N pacotes.
- Receiver bufferiza fora de ordem.
- Retransmissão individual.
- ACK individual.
- NACK indica pacote faltante.

## Janela máxima
255 pacotes.

## Testes obrigatórios

### Reordenação

| Cenário | Taxa |
|----------|-------|
| R0 | 0% |
| R1 | 10% |
| R2 | 25% |

Testar pelo menos duas janelas (ex.: 4 e 16).

## Relatório – Parte 2
1. Comparação sob latência.
2. Comparação sob perda.
3. Comparação sob reordenação.
4. Impacto do tamanho da janela.
5. Conclusão comparativa.

---

# Teste de Interoperabilidade

- Sender de um grupo ↔ Receiver de outro grupo.
- Transferência de arquivo.
- Verificação por hash.

---

# Entrega

- Grupo: até 3 alunos.
- Data: 29/06.
- Formato: ZIP contendo código, README, capturas .pcapng e relatório PDF.
- Apresentação: 29/06 e 06/07.

## Observações
- Não serão aceitos trabalhos fora do prazo.
- Trabalhos que não compilam não serão avaliados.
- Cópias recebem nota zero.
- Uso de código gerado por LLM sem compreensão demonstrada resulta em nota zero.

---

# Avaliação

| Item | Peso |
|--------|------|
| Parte 1 – Implementação Stop-and-Wait | 20% |
| Parte 1 – Relatório | 20% |
| Parte 2 – Implementação GBN e SR | 20% |
| Parte 2 – Relatório | 30% |
| Teste de interoperabilidade | 10% |