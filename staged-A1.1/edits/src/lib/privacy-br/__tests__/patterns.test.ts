/**
 * privacy-br/__tests__/patterns.test.ts
 *
 * Cobre cada um dos 12 BrPatternKind com bateria de:
 *   - Positive cases (formato + validação OK)
 *   - Negative cases (formato bate mas validação falha — confidence rebaixada)
 *   - FP bait (não deve matchar de jeito nenhum)
 *   - Boundary edges (início/fim de linha, Unicode ç/ã/ê adjacente)
 *
 * Total esperado: 100+ tests.
 *
 * gitleaks:allow — synthetic test fixtures only.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { detectBrPii, detectBrPiiByKinds } from "../detector.js";
import { redactBrPii } from "../redact.js";
import {
  VALID_CPFS_FORMATTED,
  VALID_CPFS_RAW,
  INVALID_CPFS,
  VALID_CNPJS_FORMATTED,
  VALID_CNPJS_RAW,
  INVALID_CNPJS,
  VALID_PIX_UUIDS,
  INVALID_UUIDS,
  VALID_CEPS,
  INVALID_CEPS,
  VALID_PHONES_BR,
  VALID_PIX_EMAILS,
  VALID_CARDS_BR,
  INVALID_CARDS,
  VALID_TITULOS,
  INVALID_TITULOS,
  VALID_CNHS,
  INVALID_CNHS,
  FALSE_POSITIVE_BAIT,
  PT_BR_CONTEXTS,
  COMBINED_REAL_WORLD_SAMPLE,
} from "./corpus.js";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function hasKind(text: string, kind: string): boolean {
  return detectBrPii(text).some((m) => m.kind === kind);
}

function highConfMatches(text: string, kind: string) {
  return detectBrPii(text).filter(
    (m) => m.kind === kind && m.confidence >= 0.9,
  );
}

// ─── CPF ──────────────────────────────────────────────────────────────────────

describe("CPF — valid formatted", () => {
  for (const cpf of VALID_CPFS_FORMATTED) {
    it(`detects + validates: ${cpf}`, () => {
      const matches = highConfMatches(`CPF: ${cpf} fim`, "cpf");
      assert.equal(matches.length, 1, `expected 1 high-conf match for ${cpf}`);
      assert.ok(matches[0].confidence >= 0.9, "high confidence");
    });
  }
});

describe("CPF — valid raw", () => {
  for (const cpf of VALID_CPFS_RAW) {
    it(`detects + validates: ${cpf}`, () => {
      const matches = highConfMatches(`cpf=${cpf}.`, "cpf");
      assert.equal(matches.length, 1);
    });
  }
});

describe("CPF — invalid (low confidence)", () => {
  for (const cpf of INVALID_CPFS) {
    it(`format matches but DV fails: ${cpf}`, () => {
      const matches = detectBrPii(`CPF: ${cpf} fim`);
      const cpfMatches = matches.filter((m) => m.kind === "cpf");
      // Pode ter zero matches (se boundary rejeita) ou low-confidence
      if (cpfMatches.length > 0) {
        assert.ok(
          cpfMatches[0].confidence < 0.5,
          `expected low confidence, got ${cpfMatches[0].confidence}`,
        );
      }
    });
  }
});

describe("CPF — Unicode boundary edges", () => {
  it("detects after ç/ã in context", () => {
    const text = "Inscrição CPF número 111.444.777-35 confirmada.";
    assert.ok(hasKind(text, "cpf"));
  });
  it("detects with accented words adjacent", () => {
    const text = "ação:111.444.777-35,ação";
    assert.ok(hasKind(text, "cpf"));
  });
  it("detects at start of line", () => {
    assert.ok(hasKind("111.444.777-35 é o CPF", "cpf"));
  });
  it("detects at end of line", () => {
    assert.ok(hasKind("CPF: 111.444.777-35", "cpf"));
  });
});

// ─── CNPJ ─────────────────────────────────────────────────────────────────────

describe("CNPJ — valid formatted", () => {
  for (const cnpj of VALID_CNPJS_FORMATTED) {
    it(`detects + validates: ${cnpj}`, () => {
      const matches = highConfMatches(`CNPJ: ${cnpj} fim`, "cnpj");
      assert.equal(matches.length, 1, `expected match for ${cnpj}`);
    });
  }
});

describe("CNPJ — valid raw", () => {
  for (const cnpj of VALID_CNPJS_RAW) {
    it(`detects + validates: ${cnpj}`, () => {
      const matches = highConfMatches(`cnpj=${cnpj}.`, "cnpj");
      assert.equal(matches.length, 1);
    });
  }
});

describe("CNPJ — invalid", () => {
  for (const cnpj of INVALID_CNPJS) {
    it(`format matches but DV fails: ${cnpj}`, () => {
      const ms = detectBrPii(`CNPJ ${cnpj} fim`).filter(
        (m) => m.kind === "cnpj",
      );
      if (ms.length > 0) {
        assert.ok(ms[0].confidence < 0.7, "low confidence on invalid");
      }
    });
  }
});

describe("CNPJ — preferred over CPF in overlap", () => {
  it("14-digit pure string detected as CNPJ not CPF", () => {
    // 04252011000110 = valid CNPJ, but inside it digits 1..11 form '4252011000' (not a CPF anyway)
    const text = "ID 04252011000110 fim";
    const matches = detectBrPii(text);
    const kinds = matches.map((m) => m.kind);
    assert.ok(kinds.includes("cnpj"), "should detect cnpj");
    // Should NOT also report a CPF inside the CNPJ
    const cpfMatches = matches.filter((m) => m.kind === "cpf");
    assert.equal(cpfMatches.length, 0, "no nested CPF match inside CNPJ");
  });
});

// ─── PIX UUID ────────────────────────────────────────────────────────────────

describe("PIX UUID v4", () => {
  for (const uuid of VALID_PIX_UUIDS) {
    it(`detects valid UUID v4: ${uuid}`, () => {
      assert.ok(hasKind(`chave PIX: ${uuid}.`, "pix_uuid"));
    });
  }
  for (const bad of INVALID_UUIDS) {
    it(`rejects malformed UUID: ${bad}`, () => {
      assert.ok(!hasKind(`chave ${bad} fim`, "pix_uuid"));
    });
  }
  it("UUID v1 not matched (only v4)", () => {
    const text = "id 550e8400-e29b-11d4-a716-446655440000 (v1)";
    assert.ok(!hasKind(text, "pix_uuid"));
  });
});

// ─── CEP ─────────────────────────────────────────────────────────────────────

describe("CEP", () => {
  for (const cep of VALID_CEPS) {
    it(`detects valid CEP: ${cep}`, () => {
      assert.ok(hasKind(`CEP ${cep} aqui`, "cep"));
    });
  }
  it("placeholder 00000-000 rejected", () => {
    const m = detectBrPii("CEP 00000-000 placeholder").filter(
      (x) => x.kind === "cep",
    );
    if (m.length > 0) {
      assert.ok(m[0].confidence < 0.5);
    }
  });
  for (const bad of INVALID_CEPS) {
    it(`malformed CEP not high-conf: ${bad}`, () => {
      const m = detectBrPii(`x ${bad} y`).filter((x) => x.kind === "cep");
      // Aceita zero matches (regex não bate) OU low-confidence (validate falhou)
      if (m.length > 0) {
        assert.ok(
          m[0].confidence < 0.5,
          `expected low-conf or no match for ${bad}, got conf=${m[0].confidence}`,
        );
      }
    });
  }
});

// ─── Telefone BR ─────────────────────────────────────────────────────────────

describe("Telefone BR", () => {
  for (const ph of VALID_PHONES_BR) {
    it(`detects: ${ph}`, () => {
      // Aceita telefone_br OU pix_phone (formatos com +55 podem virar pix_phone
      // dependendo da overlap resolution — ambos são PII fone).
      const matches = detectBrPii(`Tel: ${ph} fim`);
      const phoneish = matches.filter(
        (m) => m.kind === "telefone_br" || m.kind === "pix_phone",
      );
      assert.ok(
        phoneish.length >= 1,
        `expected phone/pix_phone match for "${ph}", got [${matches.map((m) => m.kind).join(",")}]`,
      );
    });
  }
  it("4-digit number not matched as phone", () => {
    const ms = detectBrPii("ramal 1234 fim");
    assert.equal(
      ms.filter((m) => m.kind === "telefone_br" || m.kind === "pix_phone").length,
      0,
    );
  });
});

// ─── PIX Email ───────────────────────────────────────────────────────────────

describe("PIX Email", () => {
  for (const email of VALID_PIX_EMAILS) {
    it(`detects: ${email}`, () => {
      assert.ok(hasKind(`PIX: ${email}.`, "pix_email"));
    });
  }
  it("non-email text not matched", () => {
    assert.ok(!hasKind("not an email", "pix_email"));
  });
  it("@ without domain not matched", () => {
    assert.ok(!hasKind("user@ fim", "pix_email"));
  });
});

// ─── Cartão BR ───────────────────────────────────────────────────────────────

describe("Cartão de crédito BR (Luhn)", () => {
  for (const c of VALID_CARDS_BR) {
    it(`detects Luhn-valid: ${c}`, () => {
      const matches = detectBrPii(`Cartão ${c} fim`).filter(
        (m) => m.kind === "cartao_br" && m.confidence >= 0.9,
      );
      assert.ok(matches.length >= 1, `expected high-conf match for ${c}`);
    });
  }
  for (const c of INVALID_CARDS) {
    it(`Luhn-invalid: ${c} produces low confidence`, () => {
      const ms = detectBrPii(`Cartão ${c} fim`).filter(
        (m) => m.kind === "cartao_br",
      );
      if (ms.length > 0) {
        assert.ok(
          ms[0].confidence < 0.7,
          `Luhn-invalid ${c} should be low-conf, got ${ms[0].confidence}`,
        );
      }
    });
  }
});

// ─── Título Eleitor ──────────────────────────────────────────────────────────

describe("Título de Eleitor", () => {
  for (const t of VALID_TITULOS) {
    it(`detects valid: ${t}`, () => {
      const ms = detectBrPii(`título ${t} fim`).filter(
        (m) => m.kind === "titulo_eleitor" && m.confidence >= 0.9,
      );
      assert.ok(ms.length >= 1, `expected high-conf match for ${t}`);
    });
  }
  for (const t of INVALID_TITULOS) {
    it(`invalid title low confidence: ${t}`, () => {
      const ms = detectBrPii(`título ${t} fim`).filter(
        (m) => m.kind === "titulo_eleitor",
      );
      if (ms.length > 0) {
        assert.ok(ms[0].confidence < 0.7);
      }
    });
  }
});

// ─── CNH ─────────────────────────────────────────────────────────────────────

describe("CNH", () => {
  for (const c of VALID_CNHS) {
    it(`detects valid CNH: ${c}`, () => {
      const matches = detectBrPiiByKinds(`CNH ${c} fim`, ["cnh"]);
      assert.ok(matches.length >= 1, `expected match for ${c}`);
      assert.ok(matches[0].confidence >= 0.7, "medium+ confidence");
    });
  }
  for (const c of INVALID_CNHS) {
    it(`invalid CNH low confidence: ${c}`, () => {
      const matches = detectBrPiiByKinds(`CNH ${c} fim`, ["cnh"]);
      if (matches.length > 0) {
        assert.ok(matches[0].confidence < 0.7);
      }
    });
  }
});

// ─── False positive bait ─────────────────────────────────────────────────────

describe("FP bait — should NOT match", () => {
  for (const text of FALSE_POSITIVE_BAIT) {
    it(`no high-conf PII: "${text.substring(0, 40)}..."`, () => {
      const matches = detectBrPii(text);
      const highConf = matches.filter((m) => m.confidence >= 0.9);
      assert.equal(
        highConf.length,
        0,
        `unexpected high-conf matches: ${highConf
          .map((m) => `${m.kind}=${m.raw}`)
          .join(", ")}`,
      );
    });
  }
});

// ─── PT-BR context ────────────────────────────────────────────────────────────

describe("PT-BR contexts (Unicode boundary)", () => {
  for (const { text, expectedKinds } of PT_BR_CONTEXTS) {
    it(`detects ${expectedKinds.join(",")} in: "${text.substring(0, 50)}..."`, () => {
      const matches = detectBrPii(text);
      for (const ek of expectedKinds) {
        assert.ok(
          matches.some((m) => m.kind === ek),
          `expected ${ek}, got [${matches.map((m) => m.kind).join(",")}]`,
        );
      }
    });
  }
});

// ─── Integration — combined sample ───────────────────────────────────────────

describe("Combined real-world sample", () => {
  it("detects multiple PII types in one document", () => {
    const matches = detectBrPii(COMBINED_REAL_WORLD_SAMPLE);
    const kinds = new Set(matches.map((m) => m.kind));
    // Expected: cpf, cnpj, cep, telefone_br, pix_email, pix_uuid, cartao_br, titulo_eleitor
    assert.ok(kinds.has("cpf"), "cpf detected");
    assert.ok(kinds.has("cnpj"), "cnpj detected");
    assert.ok(kinds.has("cep"), "cep detected");
    assert.ok(kinds.has("pix_email"), "pix_email detected");
    assert.ok(kinds.has("pix_uuid"), "pix_uuid detected");
    assert.ok(kinds.has("titulo_eleitor"), "titulo detected");
  });

  it("redactBrPii replaces all detected PII", () => {
    const r = redactBrPii(COMBINED_REAL_WORLD_SAMPLE);
    assert.ok(r.redactionCount >= 6, `expected >=6 redactions, got ${r.redactionCount}`);
    assert.ok(r.redacted.includes("[REDACTED:"), "marker present");
    // The CPF value should be gone
    assert.ok(!r.redacted.includes("111.444.777-35"), "CPF removed");
    assert.ok(!r.redacted.includes("11.222.333/0001-81"), "CNPJ removed");
    assert.ok(!r.redacted.includes("01310-100"), "CEP removed");
  });
});

// ─── Empty input ─────────────────────────────────────────────────────────────

describe("Edge: empty/invalid input", () => {
  it("empty string returns empty", () => {
    const r = redactBrPii("");
    assert.equal(r.redactionCount, 0);
    assert.equal(r.redacted, "");
  });

  it("null-like input doesn't crash", () => {
    // @ts-expect-error testing runtime safety
    const r = redactBrPii(null);
    assert.equal(r.redactionCount, 0);
  });

  it("text without any PII unchanged", () => {
    const text = "Texto sem nada de pessoal aqui.";
    const r = redactBrPii(text);
    assert.equal(r.redacted, text);
    assert.equal(r.redactionCount, 0);
  });
});
