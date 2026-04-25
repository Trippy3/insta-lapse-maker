import { ApiError, api } from "../../api/client";
/** 一度 unavailable を受けたらセッション中はネイティブ試行しない。 */
let sessionUnavailable = null;
/**
 * サーバ側で tkinter 等 OS ネイティブのダイアログを起動してパスを得る。
 * - 501 → `unavailable` を返し、呼び出し元が既存のモーダルを開く判断をする
 * - 403 / 400 などは Error を投げる (呼び出し元で表示)
 */
export async function nativePick(body) {
    if (sessionUnavailable) {
        return { kind: "unavailable", reason: sessionUnavailable.reason };
    }
    try {
        const res = await api.fsNativePick(body);
        if (res.cancelled || !res.path)
            return { kind: "cancelled" };
        return { kind: "picked", path: res.path };
    }
    catch (e) {
        if (e instanceof ApiError && e.status === 501) {
            sessionUnavailable = { reason: e.message };
            return { kind: "unavailable", reason: e.message };
        }
        throw e;
    }
}
export function getSessionUnavailableReason() {
    return sessionUnavailable?.reason ?? null;
}
export function resetNativeAvailabilityCache() {
    sessionUnavailable = null;
}
