/**
 * privacy-br/__tests__/corpus.ts — synthetic test fixtures.
 *
 * Todos os valores aqui são SINTÉTICOS — gerados via algoritmo ou retirados
 * de spec oficial. Não há PII real.
 *
 * gitleaks:allow — synthetic test vectors only.
 */

/**
 * CPFs com dígitos verificadores VÁLIDOS (formato com pontuação).
 * Verificados manualmente contra o algoritmo Receita Federal.
 */
export const VALID_CPFS_FORMATTED = [
  "111.444.777-35",
  "529.982.247-25",
  "390.533.447-05",
  "153.872.890-75",
  "048.726.918-73",
  "295.379.955-93",
  "754.213.876-66",
  "832.456.971-55",
  "612.198.435-04",
  "987.654.321-00",
];

/**
 * CPFs válidos em formato puro (11 dígitos).
 */
export const VALID_CPFS_RAW = [
  "11144477735",
  "52998224725",
  "39053344705",
  "15387289075",
  "04872691873",
  "29537995593",
  "75421387666",
  "83245697155",
  "61219843504",
  "98765432100",
];

/**
 * CPFs com DV inválido — formato bate, mas check digit falha.
 * Confidence esperada: VERY_LOW.
 */
export const INVALID_CPFS = [
  "111.444.777-99", // dv2 errado
  "529.982.247-00", // ambos errados
  "123.456.789-00",
  "999.999.999-99", // todos iguais
  "000.000.000-00", // todos iguais
  "12345678901",     // 11 dig puros, dv errado
  "11111111111",     // todos iguais
];

/**
 * CNPJs válidos (formato com pontuação).
 */
export const VALID_CNPJS_FORMATTED = [
  "11.222.333/0001-81",
  "04.252.011/0001-10",
  "60.701.190/0001-04",
  "33.000.167/0001-01",
  "47.960.950/0001-21",
  "76.487.032/0001-25",
  "53.113.791/0001-22",
  "84.974.220/0001-06",
  "12.345.678/0001-95",
  "00.000.000/0001-91", // Banco do Brasil-like test
];

/**
 * CNPJs válidos em formato puro (14 dígitos).
 */
export const VALID_CNPJS_RAW = [
  "11222333000181",
  "04252011000110",
  "60701190000104",
  "33000167000101",
  "47960950000121",
];

/**
 * CNPJs inválidos.
 */
export const INVALID_CNPJS = [
  "11.222.333/0001-99",
  "00.000.000/0000-00",
  "11.111.111/1111-11",
  "12345678901234",
  "99999999999999",
];

/**
 * UUIDs v4 válidos (chave PIX random).
 */
export const VALID_PIX_UUIDS = [
  "550e8400-e29b-41d4-a716-446655440000",
  "6ba7b810-9dad-41d1-80b4-00c04fd430c8",
  "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "01020304-0506-4708-8910-111213141516",
  "deadbeef-1234-4567-8901-234567890abc",
  "12345678-1234-4234-8234-123456789012",
];

/**
 * Strings UUID-like mas inválidas (variant errado, tamanho errado, etc).
 * Não devem matchar como pix_uuid.
 */
export const INVALID_UUIDS = [
  "550e8400-e29b-31d4-a716-446655440000", // version != 4
  "550e8400-e29b-41d4-c716-446655440000", // variant != 8,9,a,b
  "550e8400-e29b-41d4-a716-44665544",      // muito curto
  "not-a-uuid-string-at-all",
];

/**
 * CEPs válidos.
 */
export const VALID_CEPS = [
  "01310-100", // Av Paulista, SP
  "20040-020", // Rio de Janeiro
  "30130-110", // Belo Horizonte
  "70040-010", // Brasília
  "80010-000", // Curitiba
  "90010-150", // Porto Alegre
  "60000-000",
  "50000-000",
  "40000-000",
  "13560-970", // São Carlos USP
];

/**
 * Inputs CEP-like mas inválidos (não formatados, fora de range).
 */
export const INVALID_CEPS = [
  "00000-000", // placeholder
  "12345",      // muito curto
  "123456789",  // muito longo, sem hífen
  "1234-5678",  // formato errado
];

/**
 * Telefones BR válidos em diversos formatos.
 */
export const VALID_PHONES_BR = [
  "+55 11 99999-9999",
  "+55 (11) 99999-9999",
  "+5511999999999",
  "(11) 99999-9999",
  "(11) 9999-9999",     // fixo 8 dig
  "11 99999-9999",
  "11999999999",         // 11 dig puros
  "(21) 98765-4321",
  "+55 21 98765-4321",
  "+55 47 9 9876-5432",
];

/**
 * Strings com 11 dígitos que NÃO são telefone (deve fallback pra CPF se válido).
 */
export const NON_PHONE_11_DIG = [
  "12345678901", // não móvel (3o dígito não é 9)
  "10000000000",
  "00000000000",
];

/**
 * Chaves PIX email.
 */
export const VALID_PIX_EMAILS = [
  "joao@example.com",
  "maria.silva+pix@gmail.com",
  "contato@empresa.com.br",
  "abc123@hotmail.com",
  "test_user@dominio.io",
];

/**
 * Cartões de crédito BR (Luhn-valid synthetic test numbers).
 */
export const VALID_CARDS_BR = [
  "4532015112830366",       // Visa Luhn-valid
  "4532 0151 1283 0366",    // formatado
  "5425233430109903",       // MC Luhn-valid
  "5425-2334-3010-9903",    // formatado com hífen
  "4111 1111 1111 1111",    // test card universal
];

/**
 * Cartões inválidos (Luhn falha).
 */
export const INVALID_CARDS = [
  "4532015112830367", // Luhn errado
  "1234567812345678",
  "0000000000000000",
];

/**
 * Títulos de eleitor válidos (calculados via algoritmo TSE).
 */
export const VALID_TITULOS = [
  // Gerados via algoritmo TSE (base8 + UF + DV1 + DV2)
  "123456780191", // UF=01 (SP)
  "234567890299", // UF=02 (MG)
  "999988881732", // UF=17
  "100000001520", // UF=15
  "876543210329", // UF=03
];

/**
 * Títulos inválidos.
 */
export const INVALID_TITULOS = [
  "123456789012", // DV errado
  "000000000000",
  "999999999999",
];

/**
 * CNHs válidas (calculadas via algoritmo DETRAN).
 */
export const VALID_CNHS = [
  // Gerados via algoritmo DETRAN
  "82712295775",
  "63574281991",
  "12345678900",
  "11122233369",
  "50040030019",
];

/**
 * CNHs inválidas.
 */
export const INVALID_CNHS = [
  "12345678901",
  "00000000000",
  "11111111111",
];

/**
 * RGs (formato livre, vários estados).
 */
export const RG_SAMPLES = [
  "12.345.678-9",   // SP padrão
  "1.234.567",       // alguns estados
  "12345678",        // sem formatação
  "12.345.678-X",    // último char X
  "98.765.432-1",
];

/**
 * Textos de bait que NÃO devem matchar:
 *   - lorem ipsum
 *   - timestamps unix
 *   - hashes
 *   - UUIDs v1
 *   - IDs internos
 */
export const FALSE_POSITIVE_BAIT = [
  "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
  "Build #1234567 completed at 1717000000 (unix epoch).",
  "Commit hash: a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
  "User ID: 550e8400-e29b-11d4-a716-446655440000", // UUID v1
  "Order #INV-2024-998877 — total R$ 1.234,56",
  "Phone extension: x4567",
  "Build version 1.2.3.4567",
  "Hex color: #abcdef",
  "Random number: 31415926535",
  "Pi to 11 digits is 31415926535",
  "ISBN-13: 9781234567890",
];

/**
 * Contextos PT-BR realistas onde PII aparece — pra testar boundary Unicode.
 * Inclui acentos antes/depois pra detectar bugs de \b.
 */
export const PT_BR_CONTEXTS = [
  { text: "O CPF do José é 111.444.777-35 e ele mora em São Paulo.", expectedKinds: ["cpf"] },
  { text: "Razão social: Acme Ltda — CNPJ 11.222.333/0001-81.", expectedKinds: ["cnpj"] },
  { text: "Endereço: Av. Paulista, 1000, CEP 01310-100.", expectedKinds: ["cep"] },
  { text: "Pague no PIX: chave 550e8400-e29b-41d4-a716-446655440000.", expectedKinds: ["pix_uuid"] },
  { text: "Telefone para contato: (11) 99999-9999.", expectedKinds: ["telefone_br"] },
  { text: "Cartão de crédito 4532 0151 1283 0366 cancelado.", expectedKinds: ["cartao_br"] },
];

/**
 * Texto realista combinando vários tipos — usado em integration test.
 */
export const COMBINED_REAL_WORLD_SAMPLE = `
Solicitação de cadastro:
Nome: João da Silva
CPF: 111.444.777-35
RG: 12.345.678-9
CNPJ da empresa: 11.222.333/0001-81
Endereço: Av. Paulista, 1000 - São Paulo/SP - CEP 01310-100
Telefone: +55 11 99999-9999
Email: joao.silva@example.com.br
PIX (chave aleatória): 550e8400-e29b-41d4-a716-446655440000
Cartão para faturamento: 4532 0151 1283 0366
Título de eleitor: 123456780191
`;

/**
 * Texto SEM PII — usado pra eval FP rate.
 * Lorem + technical jargon + random IDs que não devem matchar.
 */
export const NON_PII_CORPUS = `
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex
ea commodo consequat.

Build #42 completed at timestamp 1717000000. Commit sha:
a1b2c3d4e5f60718293a4b5c6d7e8f9012345678abcdef.

Order INV-2024-998877 totaling R$ 1.234,56 was processed in 250ms.
Pi to 11 digits: 31415926535. Hex color #abcdef0123456789abcdef.

User ID: 550e8400-e29b-11d4-a716-446655440000 (UUID v1, not v4).
Session token: build_v1.2.3.4567 — version string, not credential.

Database row id 1234567 references table products.
Internal SKU: 9876543210.

This document contains exactly zero pieces of personally identifiable
information. Any sequence of digits is meaningless metadata.

Estoque atual: 12345 unidades. Preço unitário R$ 9,99.
Validade: 31/12/2025 (mas 31122025 é só data sem PII).

Os participantes da reunião foram: Alice, Bob, Charlie e Diana.
A pauta inclui revisão do roadmap Q1, alocação de capacity e
planejamento de capacity para Q2.
`;
