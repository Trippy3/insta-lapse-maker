import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * 絶対パス表示 + ブラウズボタン。`<input type="text">` の置き換えとして使う。
 * ユーザーが直接パスを手入力することはできない (readonly)。
 */
export function PathField({ value, placeholder, onBrowse, onClear, browseLabel = "選択...", }) {
    return (_jsxs("div", { className: "path-field", title: value ?? placeholder, children: [value ? (_jsx("span", { className: "path-value", children: value })) : (_jsx("span", { className: "path-placeholder", children: placeholder })), _jsx("button", { onClick: onBrowse, children: browseLabel }), onClear && value && (_jsx("button", { onClick: onClear, title: "\u30AF\u30EA\u30A2", children: "\u00D7" }))] }));
}
