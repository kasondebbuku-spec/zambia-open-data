import { describe, expect, it } from "vitest";
import { kwacha, kwachaShort, sentenceCase, signedKwachaShort, signedPct, tidyName } from "@/lib/format";
import { storiesQuery } from "@/lib/query";

describe("money", () => {
  it("writes full kwacha with separators", () => {
    expect(kwacha(1079607654)).toBe("K1,079,607,654");
  });

  it("shortens for headlines and bars", () => {
    expect(kwachaShort(1079607654)).toBe("K1.08 bn");
    expect(kwachaShort(732090165)).toBe("K732.1 m");
    expect(kwachaShort(159016485)).toBe("K159 m");
    expect(kwachaShort(889_500)).toBe("K889.5 k");
    expect(kwachaShort(950)).toBe("K950");
    expect(kwachaShort(1_000_000_000)).toBe("K1 bn");
  });

  it("signs changes with a real minus", () => {
    expect(signedKwachaShort(37_957_560)).toBe("+K38 m");
    expect(signedKwachaShort(-11_332_335)).toBe("−K11.3 m");
    expect(signedPct(47.5)).toBe("+47.5%");
    expect(signedPct(-17.7)).toBe("−17.7%");
    expect(signedPct(0)).toBe("0%");
  });
});

describe("council text", () => {
  it("calms all-caps headlines but keeps acronyms and place names", () => {
    expect(sentenceCase("LCC HANDS OVER K3.7M WORTH OF CDF LOANS TO CHAWAMA CONSTITUENCY")).toBe(
      "LCC hands over K3.7M worth of CDF loans to Chawama constituency",
    );
    expect(sentenceCase("PROGRESS UPDATE: CONSTRUCTION OF RECREATION CENTRE IN MATERO WARD 32")).toBe(
      "Progress update: Construction of recreation centre in Matero ward 32",
    );
  });

  it("leaves normal headlines alone", () => {
    expect(sentenceCase("Works are underway to pave some roads in Kabwata Constituency.")).toBe(
      "Works are underway to pave some roads in Kabwata Constituency.",
    );
  });

  it("fixes the books' typos only where safe", () => {
    expect(tidyName("District Health servcies")).toBe("District Health services");
  });
});

describe("story query", () => {
  it("sends only the filters that are set", () => {
    expect(storiesQuery({ constituency: "Matero", q: "market & clinic" })).toBe(
      "constituency=Matero&q=market+%26+clinic&limit=12",
    );
    expect(storiesQuery({ sector: "health", limit: 3, offset: 24 })).toBe("sector=health&limit=3&offset=24");
  });
});
