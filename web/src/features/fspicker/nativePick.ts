import { ApiError, api } from "../../api/client";
import type { NativePickBody } from "../../types/project";

/**
 * 二段構えピッカーの結果。
 * - picked: ユーザーが選択完了 (絶対パス)
 * - cancelled: ネイティブダイアログは開いたがキャンセルされた (モーダルは開かない)
 * - unavailable: 501 — UI 側の内蔵モーダルへフォールバックする合図
 */
export type NativePickOutcome =
  | { kind: "picked"; path: string }
  | { kind: "cancelled" }
  | { kind: "unavailable"; reason: string };

/** 一度 unavailable を受けたらセッション中はネイティブ試行しない。 */
let sessionUnavailable: { reason: string } | null = null;

/**
 * サーバ側で tkinter 等 OS ネイティブのダイアログを起動してパスを得る。
 * - 501 → `unavailable` を返し、呼び出し元が既存のモーダルを開く判断をする
 * - 403 / 400 などは Error を投げる (呼び出し元で表示)
 */
export async function nativePick(body: NativePickBody): Promise<NativePickOutcome> {
  if (sessionUnavailable) {
    return { kind: "unavailable", reason: sessionUnavailable.reason };
  }
  try {
    const res = await api.fsNativePick(body);
    if (res.cancelled || !res.path) return { kind: "cancelled" };
    return { kind: "picked", path: res.path };
  } catch (e) {
    if (e instanceof ApiError && e.status === 501) {
      sessionUnavailable = { reason: e.message };
      return { kind: "unavailable", reason: e.message };
    }
    throw e;
  }
}

export function getSessionUnavailableReason(): string | null {
  return sessionUnavailable?.reason ?? null;
}

export function resetNativeAvailabilityCache(): void {
  sessionUnavailable = null;
}
