module.exports = [
"[project]/src/components/PublicLayout.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/navigation.jsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$utils$2f$auth$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/utils/auth.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/components/ui/Button.jsx [app-ssr] (ecmascript)");
'use client';
;
;
;
;
;
function PublicLayout({ children }) {
    const navigate = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useNavigate"])();
    const location = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useLocation"])();
    const [authenticated, setAuthenticated] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        setAuthenticated((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$utils$2f$auth$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["isAuthenticated"])());
    }, [
        location.pathname
    ]);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const handleStorage = ()=>{
            setAuthenticated((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$utils$2f$auth$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["isAuthenticated"])());
        };
        window.addEventListener("storage", handleStorage);
        return ()=>window.removeEventListener("storage", handleStorage);
    }, []);
    const handleLogout = ()=>{
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$utils$2f$auth$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["logoutUser"])();
        setAuthenticated(false);
        navigate("/", {
            replace: true
        });
    };
    const navigateToDashboard = ()=>{
        navigate("/dashboard");
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        style: styles.wrapper,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                style: styles.header,
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    style: styles.container,
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        style: styles.navbar,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Link"], {
                                to: "/",
                                style: styles.logo,
                                children: "RankCare"
                            }, void 0, false, {
                                fileName: "[project]/src/components/PublicLayout.jsx",
                                lineNumber: 40,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                                style: styles.nav,
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Link"], {
                                        to: "/pricing",
                                        style: styles.navLink,
                                        children: "Pricing"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/PublicLayout.jsx",
                                        lineNumber: 45,
                                        columnNumber: 15
                                    }, this),
                                    authenticated ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        style: styles.authActions,
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                type: "button",
                                                variant: "primary",
                                                onClick: navigateToDashboard,
                                                children: "Dashboard"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/PublicLayout.jsx",
                                                lineNumber: 49,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                type: "button",
                                                variant: "danger",
                                                onClick: handleLogout,
                                                children: "Logout"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/PublicLayout.jsx",
                                                lineNumber: 52,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/src/components/PublicLayout.jsx",
                                        lineNumber: 48,
                                        columnNumber: 17
                                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        style: styles.authActions,
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Link"], {
                                                to: "/login",
                                                style: styles.dashboardBtn,
                                                children: "Login"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/PublicLayout.jsx",
                                                lineNumber: 58,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Link"], {
                                                to: "/register",
                                                style: styles.logoutBtn,
                                                children: "Register"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/PublicLayout.jsx",
                                                lineNumber: 61,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/src/components/PublicLayout.jsx",
                                        lineNumber: 57,
                                        columnNumber: 17
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/src/components/PublicLayout.jsx",
                                lineNumber: 44,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/src/components/PublicLayout.jsx",
                        lineNumber: 39,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/src/components/PublicLayout.jsx",
                    lineNumber: 38,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/src/components/PublicLayout.jsx",
                lineNumber: 37,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
                style: styles.main,
                children: children
            }, void 0, false, {
                fileName: "[project]/src/components/PublicLayout.jsx",
                lineNumber: 71,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("footer", {
                style: styles.footer,
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    style: styles.container,
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        style: styles.footerText,
                        children: "© 2026 RankCare. SEO insights, rank tracking, and reporting."
                    }, void 0, false, {
                        fileName: "[project]/src/components/PublicLayout.jsx",
                        lineNumber: 75,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/src/components/PublicLayout.jsx",
                    lineNumber: 74,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/src/components/PublicLayout.jsx",
                lineNumber: 73,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/src/components/PublicLayout.jsx",
        lineNumber: 36,
        columnNumber: 5
    }, this);
}
const styles = {
    wrapper: {
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "#f8fafc",
        color: "#0f172a"
    },
    header: {
        background: "#ffffff",
        borderBottom: "1px solid #e2e8f0",
        position: "sticky",
        top: 0,
        zIndex: 100
    },
    container: {
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "0 20px"
    },
    navbar: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        minHeight: "72px",
        gap: "20px",
        flexWrap: "wrap"
    },
    logo: {
        fontSize: "24px",
        fontWeight: 700,
        color: "#0f172a",
        textDecoration: "none"
    },
    nav: {
        display: "flex",
        alignItems: "center",
        gap: "18px",
        flexWrap: "wrap"
    },
    navLink: {
        color: "#334155",
        textDecoration: "none",
        fontSize: "15px",
        fontWeight: 500
    },
    main: {
        flex: 1
    },
    footer: {
        borderTop: "1px solid #e2e8f0",
        background: "#ffffff",
        marginTop: "40px"
    },
    footerText: {
        padding: "20px 0",
        color: "#64748b",
        fontSize: "14px"
    },
    authActions: {
        display: "flex",
        alignItems: "center",
        gap: "12px"
    },
    dashboardBtn: {
        background: "#2563eb",
        color: "#ffffff",
        padding: "10px 16px",
        borderRadius: "10px",
        textDecoration: "none",
        fontSize: "14px",
        fontWeight: 600,
        border: "none",
        cursor: "pointer"
    },
    logoutBtn: {
        background: "#ef4444",
        color: "#ffffff",
        padding: "10px 16px",
        borderRadius: "10px",
        textDecoration: "none",
        fontSize: "14px",
        fontWeight: 600,
        border: "none",
        cursor: "pointer"
    }
};
const __TURBOPACK__default__export__ = PublicLayout;
}),
"[project]/src/components/ui/Alert.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__AlertCircle$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/circle-alert.mjs [app-ssr] (ecmascript) <export default as AlertCircle>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$check$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__CheckCircle2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/circle-check.mjs [app-ssr] (ecmascript) <export default as CheckCircle2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$info$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Info$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/info.mjs [app-ssr] (ecmascript) <export default as Info>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$triangle$2d$alert$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__TriangleAlert$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/triangle-alert.mjs [app-ssr] (ecmascript) <export default as TriangleAlert>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/x.mjs [app-ssr] (ecmascript) <export default as X>");
'use client';
;
;
/**
 * Alert Component
 * 
 * A notification component for displaying important messages.
 * Supports multiple variants, optional dismissal, and custom actions.
 * 
 * @param {string} variant - Alert type: 'warning' | 'error' | 'success' | 'info' | 'plain'
 * @param {string} title - Optional alert title
 * @param {string} message - Alert message content
 * @param {React.ReactNode} children - Custom content
 * @param {React.ReactNode} action - Optional action button or content
 * @param {boolean} dismissible - Whether alert can be dismissed
 * @param {Function} onDismiss - Callback when alert is dismissed
 * @param {string} className - Additional CSS classes
 */ const VARIANT_STYLES = {
    warning: {
        wrapper: 'border-amber-200 bg-amber-50 text-amber-800',
        icon: 'text-amber-600'
    },
    error: {
        wrapper: 'border-red-200 bg-red-50 text-red-700',
        icon: 'text-red-600'
    },
    success: {
        wrapper: 'border-emerald-200 bg-emerald-50 text-emerald-700',
        icon: 'text-emerald-600'
    },
    info: {
        wrapper: 'border-sky-200 bg-sky-50 text-sky-700',
        icon: 'text-sky-600'
    },
    plain: {
        wrapper: 'border-slate-200 bg-white text-slate-500',
        icon: 'text-slate-600'
    }
};
const VARIANT_ICONS = {
    warning: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$triangle$2d$alert$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__TriangleAlert$3e$__["TriangleAlert"],
    error: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__AlertCircle$3e$__["AlertCircle"],
    success: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$check$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__CheckCircle2$3e$__["CheckCircle2"],
    info: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$info$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Info$3e$__["Info"],
    plain: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$info$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Info$3e$__["Info"]
};
function Alert({ variant = 'info', title, message, children, action, dismissible = false, onDismiss, className = '' }) {
    const styles = VARIANT_STYLES[variant] || VARIANT_STYLES.info;
    const Icon = VARIANT_ICONS[variant] || VARIANT_ICONS.info;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: `rounded-2xl border px-4 py-3 text-sm ${styles.wrapper} ${className}`,
        role: "alert",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex items-start gap-3",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(Icon, {
                    className: `mt-0.5 h-5 w-5 shrink-0 ${styles.icon}`,
                    "aria-hidden": "true"
                }, void 0, false, {
                    fileName: "[project]/src/components/ui/Alert.jsx",
                    lineNumber: 69,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "min-w-0 flex-1",
                    children: [
                        title ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "font-semibold",
                            children: title
                        }, void 0, false, {
                            fileName: "[project]/src/components/ui/Alert.jsx",
                            lineNumber: 73,
                            columnNumber: 13
                        }, this) : null,
                        message ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: title ? 'mt-1' : '',
                            children: message
                        }, void 0, false, {
                            fileName: "[project]/src/components/ui/Alert.jsx",
                            lineNumber: 79,
                            columnNumber: 13
                        }, this) : null,
                        children ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: title || message ? 'mt-1' : '',
                            children: children
                        }, void 0, false, {
                            fileName: "[project]/src/components/ui/Alert.jsx",
                            lineNumber: 85,
                            columnNumber: 13
                        }, this) : null,
                        action ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "mt-3",
                            children: action
                        }, void 0, false, {
                            fileName: "[project]/src/components/ui/Alert.jsx",
                            lineNumber: 91,
                            columnNumber: 13
                        }, this) : null
                    ]
                }, void 0, true, {
                    fileName: "[project]/src/components/ui/Alert.jsx",
                    lineNumber: 71,
                    columnNumber: 9
                }, this),
                dismissible && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                    onClick: onDismiss,
                    className: "flex-shrink-0 text-slate-400 hover:text-slate-600 transition-colors",
                    "aria-label": "Dismiss alert",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__["X"], {
                        className: "h-4 w-4"
                    }, void 0, false, {
                        fileName: "[project]/src/components/ui/Alert.jsx",
                        lineNumber: 103,
                        columnNumber: 13
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/src/components/ui/Alert.jsx",
                    lineNumber: 98,
                    columnNumber: 11
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/src/components/ui/Alert.jsx",
            lineNumber: 68,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/src/components/ui/Alert.jsx",
        lineNumber: 64,
        columnNumber: 5
    }, this);
}
const __TURBOPACK__default__export__ = Alert;
}),
"[project]/src/components/ui/Button.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
'use client';
;
/**
 * Button Component
 * 
 * A versatile button component with multiple variants and sizes.
 * Supports loading states, icons, and full width option.
 * 
 * @param {React.ReactNode} children - Button content
 * @param {string} variant - Button style: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
 * @param {string} size - Button size: 'sm' | 'md' | 'lg'
 * @param {boolean} disabled - Disable the button
 * @param {boolean} loading - Show loading spinner
 * @param {boolean} fullWidth - Make button full width
 * @param {string} className - Additional CSS classes
 * @param {string} type - HTML button type
 * @param {React.ReactNode} leftIcon - Icon to display on the left
 * @param {React.ReactNode} rightIcon - Icon to display on the right
 */ function Button({ children, variant = 'primary', size = 'md', disabled, loading, fullWidth = false, className = '', type = 'button', leftIcon, rightIcon, ...props }) {
    const variantStyles = {
        primary: 'bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-200',
        secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-200',
        danger: 'bg-danger text-white hover:bg-red-600 focus:ring-red-200',
        ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-200',
        outline: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus:ring-slate-200'
    };
    const sizeStyles = {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2.5 text-sm',
        lg: 'px-6 py-3 text-base'
    };
    const base = [
        'inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition focus:outline-none focus:ring-4 focus:ring-offset-0',
        sizeStyles[size],
        variantStyles[variant],
        fullWidth ? 'w-full' : '',
        disabled || loading ? 'opacity-60 cursor-not-allowed' : '',
        className
    ].filter(Boolean).join(' ');
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
        type: type,
        className: base,
        disabled: disabled || loading,
        "aria-busy": loading,
        ...props,
        children: [
            loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "inline-flex items-center gap-2",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "h-4 w-4 animate-spin rounded-full border-2 border-current/30 border-t-current",
                        "aria-hidden": "true"
                    }, void 0, false, {
                        fileName: "[project]/src/components/ui/Button.jsx",
                        lineNumber: 67,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "sr-only",
                        children: "Loading..."
                    }, void 0, false, {
                        fileName: "[project]/src/components/ui/Button.jsx",
                        lineNumber: 68,
                        columnNumber: 11
                    }, this),
                    children
                ]
            }, void 0, true, {
                fileName: "[project]/src/components/ui/Button.jsx",
                lineNumber: 66,
                columnNumber: 9
            }, this),
            !loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
                children: [
                    leftIcon && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "flex-shrink-0",
                        "aria-hidden": "true",
                        children: leftIcon
                    }, void 0, false, {
                        fileName: "[project]/src/components/ui/Button.jsx",
                        lineNumber: 74,
                        columnNumber: 24
                    }, this),
                    children,
                    rightIcon && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "flex-shrink-0",
                        "aria-hidden": "true",
                        children: rightIcon
                    }, void 0, false, {
                        fileName: "[project]/src/components/ui/Button.jsx",
                        lineNumber: 76,
                        columnNumber: 25
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/src/components/ui/Button.jsx",
                lineNumber: 73,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/src/components/ui/Button.jsx",
        lineNumber: 58,
        columnNumber: 5
    }, this);
}
const __TURBOPACK__default__export__ = Button;
}),
"[project]/src/config/pricing.js [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "PLANS",
    ()=>PLANS,
    "PLAN_COMPARISON",
    ()=>PLAN_COMPARISON,
    "TRIAL_DAYS",
    ()=>TRIAL_DAYS,
    "VALID_PLAN_KEYS",
    ()=>VALID_PLAN_KEYS
]);
'use client';
const TRIAL_DAYS = 7;
const PLANS = [
    {
        key: "free_trial",
        name: "Free Trial",
        monthlyPrice: 0,
        yearlyPrice: 0,
        description: "7-day free trial to test RankCare.",
        highlighted: false,
        cta: "Start Free Trial",
        refreshFrequency: "weekly",
        limits: {
            projects: 1,
            keywords: 5,
            competitorsPerProject: 3,
            reportsPerMonth: 1,
            teamMembers: 1,
            aioKeywordsMonitored: 0,
            keywordResearchCreditsPerMonth: 10
        },
        features: [
            "1 project",
            "Track up to 5 keywords",
            "Weekly rank updates",
            "1 report / month",
            "Limited keyword research",
            "No AIO tracking"
        ]
    },
    {
        key: "starter",
        name: "Starter",
        monthlyPrice: 999,
        yearlyPrice: 9599,
        description: "Best for freelancers and small websites starting SEO tracking.",
        highlighted: false,
        cta: "Start Starter",
        refreshFrequency: "weekly",
        limits: {
            projects: 1,
            keywords: 100,
            competitorsPerProject: 3,
            reportsPerMonth: 1,
            teamMembers: 1,
            aioKeywordsMonitored: 0,
            keywordResearchCreditsPerMonth: 50
        },
        features: [
            "1 project",
            "Track up to 100 keywords",
            "Weekly rank updates",
            "1 report / month",
            "50 keyword research credits / month",
            "No AIO tracking",
            "Email support"
        ]
    },
    {
        key: "pro",
        name: "Pro",
        monthlyPrice: 2499,
        yearlyPrice: 23999,
        description: "Ideal for growing businesses that need stronger reporting and tracking.",
        highlighted: true,
        cta: "Start Pro",
        refreshFrequency: "weekly",
        limits: {
            projects: 3,
            keywords: 200,
            competitorsPerProject: 6,
            reportsPerMonth: 6,
            teamMembers: 3,
            aioKeywordsMonitored: 50,
            keywordResearchCreditsPerMonth: 200
        },
        features: [
            "Up to 3 projects",
            "Track up to 200 keywords",
            "Weekly rank updates",
            "6 reports / month",
            "200 keyword research credits / month",
            "50 AIO tracked keywords",
            "Competitor tracking",
            "Priority support"
        ]
    },
    {
        key: "agency",
        name: "Agency",
        monthlyPrice: 4999,
        yearlyPrice: 47999,
        description: "Built for agencies handling multiple clients and organized client delivery.",
        highlighted: false,
        cta: "Start Agency",
        refreshFrequency: "weekly",
        limits: {
            projects: 10,
            keywords: 500,
            competitorsPerProject: 10,
            reportsPerMonth: 25,
            teamMembers: 5,
            aioKeywordsMonitored: 200,
            keywordResearchCreditsPerMonth: 500
        },
        features: [
            "Up to 10 projects",
            "Track up to 500 keywords",
            "Weekly rank updates",
            "25 reports / month",
            "500 keyword research credits / month",
            "200 AIO tracked keywords",
            "Team access",
            "Premium support"
        ]
    }
];
const PLAN_COMPARISON = [
    {
        label: "Projects",
        freeTrial: "1",
        starter: "1",
        pro: "3",
        agency: "10"
    },
    {
        label: "Tracked keywords",
        freeTrial: "5",
        starter: "100",
        pro: "200",
        agency: "500"
    },
    {
        label: "Competitors / project",
        freeTrial: "3",
        starter: "3",
        pro: "6",
        agency: "10"
    },
    {
        label: "Reports / month",
        freeTrial: "1",
        starter: "1",
        pro: "6",
        agency: "25"
    },
    {
        label: "Team members",
        freeTrial: "1",
        starter: "1",
        pro: "3",
        agency: "5"
    },
    {
        label: "Refresh frequency",
        freeTrial: "Weekly",
        starter: "Weekly",
        pro: "Weekly",
        agency: "Weekly"
    },
    {
        label: "AIO tracked keywords",
        freeTrial: "0",
        starter: "0",
        pro: "50",
        agency: "200"
    },
    {
        label: "Keyword research credits / month",
        freeTrial: "10",
        starter: "50",
        pro: "200",
        agency: "500"
    }
];
const VALID_PLAN_KEYS = PLANS.map((plan)=>plan.key);
}),
"[project]/src/lib/navigation.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Link",
    ()=>Link,
    "NavLink",
    ()=>NavLink,
    "Navigate",
    ()=>Navigate,
    "Outlet",
    ()=>Outlet,
    "useLocation",
    ()=>useLocation,
    "useNavigate",
    ()=>useNavigate,
    "useSearchParams",
    ()=>useSearchParams
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
;
;
function Link({ to, href, children, style, className, ...props }) {
    const path = to || href;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
        href: path,
        className: className,
        ...props,
        children: children
    }, void 0, false, {
        fileName: "[project]/src/lib/navigation.jsx",
        lineNumber: 10,
        columnNumber: 5
    }, this);
}
function useNavigate() {
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    return (to, options)=>{
        if (options && options.replace) {
            router.replace(to);
        } else {
            router.push(to);
        }
    };
}
function useLocation() {
    const pathname = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["usePathname"])();
    const [search, setSearch] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('');
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        setSearch(window.location.search);
    }, [
        pathname
    ]);
    return {
        pathname,
        search,
        hash: '',
        state: null,
        key: ''
    };
}
function useSearchParams() {
    const [search, setSearch] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('');
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        setSearch(window.location.search);
    }, [
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["usePathname"])()
    ]);
    const params = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMemo"])(()=>new URLSearchParams(search), [
        search
    ]);
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    const setSearchParams = (newParams, options)=>{
        const url = new URL(window.location.href);
        url.search = '';
        if (newParams instanceof URLSearchParams) {
            newParams.forEach((v, k)=>url.searchParams.set(k, v));
        } else if (typeof newParams === 'object' && newParams !== null) {
            Object.entries(newParams).forEach(([k, v])=>url.searchParams.set(k, String(v)));
        }
        const fullPath = `${window.location.pathname}${url.search}`;
        if (options && options.replace) {
            router.replace(fullPath);
        } else {
            router.push(fullPath);
        }
    };
    return [
        params,
        setSearchParams
    ];
}
function Navigate({ to, replace, state, ...props }) {
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        if (replace) {
            router.replace(to);
        } else {
            router.push(to);
        }
    }, [
        to,
        replace,
        state,
        router
    ]);
    return null;
}
function NavLink({ to, href, className, activeClassName, end, ...props }) {
    const pathname = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["usePathname"])();
    const path = to || href;
    const isActive = end ? pathname === path : pathname.startsWith(path);
    const cls = `${className || ''} ${isActive ? activeClassName || 'active' : ''}`.trim();
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
        href: path,
        className: cls,
        ...props
    }, void 0, false, {
        fileName: "[project]/src/lib/navigation.jsx",
        lineNumber: 91,
        columnNumber: 10
    }, this);
}
function Outlet({ children }) {
    return children;
}
}),
"[project]/src/utils/auth.js [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "clearStoredUser",
    ()=>clearStoredUser,
    "getAccessToken",
    ()=>getAccessToken,
    "getStoredUser",
    ()=>getStoredUser,
    "isAuthenticated",
    ()=>isAuthenticated,
    "logoutUser",
    ()=>logoutUser,
    "removeAccessToken",
    ()=>removeAccessToken,
    "setAccessToken",
    ()=>setAccessToken,
    "setStoredUser",
    ()=>setStoredUser
]);
'use client';
const ACCESS_TOKEN_KEY = "accessToken";
const USER_KEY = "user";
function getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
}
function setAccessToken(token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
}
function removeAccessToken() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
}
function getStoredUser() {
    try {
        const raw = localStorage.getItem("user");
        return raw ? JSON.parse(raw) : null;
    } catch  {
        return null;
    }
}
function isAuthenticated() {
    try {
        return Boolean(localStorage.getItem("accessToken"));
    } catch  {
        return false;
    }
}
function setStoredUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}
function clearStoredUser() {
    localStorage.removeItem(USER_KEY);
}
function logoutUser() {
    removeAccessToken();
    clearStoredUser();
}
}),
"[project]/src/views/RegisterPage.jsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/navigation.jsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/config/pricing.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/components/ui/Button.jsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Alert$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/components/ui/Alert.jsx [app-ssr] (ecmascript)");
'use client';
;
;
;
;
;
;
;
function RegisterPage() {
    const navigate = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useNavigate"])();
    const location = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useLocation"])();
    const searchParams = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMemo"])(()=>new URLSearchParams(location.search), [
        location.search
    ]);
    const initialPlanFromUrl = searchParams.get("plan")?.toLowerCase() || "starter";
    const safeInitialPlan = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["VALID_PLAN_KEYS"].includes(initialPlanFromUrl) ? initialPlanFromUrl : "starter";
    const [form, setForm] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])({
        name: "",
        email: "",
        password: "",
        selectedPlan: safeInitialPlan
    });
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
    const [success, setSuccess] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
    const selectedPlanMeta = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["PLANS"].find((plan)=>plan.key === form.selectedPlan) || __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["PLANS"][0];
    const handleChange = (e)=>{
        const { name, value } = e.target;
        setForm((prev)=>({
                ...prev,
                [name]: value
            }));
    };
    const handlePlanSelect = (planKey)=>{
        setForm((prev)=>({
                ...prev,
                selectedPlan: planKey
            }));
    };
    const handleSubmit = async (e)=>{
        e.preventDefault();
        setError("");
        setSuccess("");
        setLoading(true);
        try {
            await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["registerApi"])({
                name: form.name,
                email: form.email,
                password: form.password,
                selectedPlan: form.selectedPlan
            });
            setSuccess("Registration successful. Please verify your email before logging in.");
            setTimeout(()=>{
                navigate(`/login?emailVerificationPending=true&plan=${form.selectedPlan}`);
            }, 700);
        } catch (err) {
            setError(err.message || "Something went wrong");
        } finally{
            setLoading(false);
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        style: styles.wrapper,
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            style: styles.card,
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                    style: styles.title,
                    children: "Register"
                }, void 0, false, {
                    fileName: "[project]/src/views/RegisterPage.jsx",
                    lineNumber: 74,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    style: styles.subtitle,
                    children: [
                        "Create your RankCare account and start your ",
                        __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["TRIAL_DAYS"],
                        "-day trial"
                    ]
                }, void 0, true, {
                    fileName: "[project]/src/views/RegisterPage.jsx",
                    lineNumber: 75,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    style: styles.planBox,
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            style: styles.planBoxLabel,
                            children: "Selected plan"
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 78,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            style: styles.planList,
                            children: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["PLANS"].map((plan)=>{
                                const active = form.selectedPlan === plan.key;
                                return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                    type: "button",
                                    variant: active ? 'primary' : 'outline',
                                    size: "sm",
                                    onClick: ()=>handlePlanSelect(plan.key),
                                    style: styles.planChip,
                                    children: plan.name
                                }, plan.key, false, {
                                    fileName: "[project]/src/views/RegisterPage.jsx",
                                    lineNumber: 85,
                                    columnNumber: 17
                                }, this);
                            })
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 80,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            style: styles.planSummary,
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    style: styles.planSummaryTitle,
                                    children: [
                                        selectedPlanMeta.name,
                                        " plan selected"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/src/views/RegisterPage.jsx",
                                    lineNumber: 100,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    style: styles.planSummaryText,
                                    children: [
                                        "Trial: ",
                                        __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$config$2f$pricing$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["TRIAL_DAYS"],
                                        " days, then continue with the ",
                                        selectedPlanMeta.name,
                                        " plan when billing is enabled."
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/src/views/RegisterPage.jsx",
                                    lineNumber: 103,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 99,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/src/views/RegisterPage.jsx",
                    lineNumber: 77,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                    onSubmit: handleSubmit,
                    style: styles.form,
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            style: styles.input,
                            type: "text",
                            name: "name",
                            placeholder: "Full name",
                            value: form.name,
                            onChange: handleChange
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 110,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            style: styles.input,
                            type: "email",
                            name: "email",
                            placeholder: "Email",
                            value: form.email,
                            onChange: handleChange
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 119,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            style: styles.input,
                            type: "password",
                            name: "password",
                            placeholder: "Password",
                            value: form.password,
                            onChange: handleChange
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 128,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            type: "hidden",
                            name: "selectedPlan",
                            value: form.selectedPlan,
                            readOnly: true
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 137,
                            columnNumber: 11
                        }, this),
                        error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Alert$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                            variant: "error",
                            message: error
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 139,
                            columnNumber: 21
                        }, this),
                        success && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Alert$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                            variant: "success",
                            message: success
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 140,
                            columnNumber: 23
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$ui$2f$Button$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                            type: "submit",
                            disabled: loading,
                            loading: loading,
                            fullWidth: true,
                            children: "Start trial"
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 142,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/src/views/RegisterPage.jsx",
                    lineNumber: 109,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    style: styles.footerText,
                    children: [
                        "Already have an account? ",
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$navigation$2e$jsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Link"], {
                            to: "/login",
                            children: "Login"
                        }, void 0, false, {
                            fileName: "[project]/src/views/RegisterPage.jsx",
                            lineNumber: 148,
                            columnNumber: 36
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/src/views/RegisterPage.jsx",
                    lineNumber: 147,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/src/views/RegisterPage.jsx",
            lineNumber: 73,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/src/views/RegisterPage.jsx",
        lineNumber: 72,
        columnNumber: 5
    }, this);
}
const styles = {
    wrapper: {
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#f5f7fb",
        padding: "24px"
    },
    card: {
        width: "100%",
        maxWidth: "460px",
        background: "#fff",
        padding: "32px",
        borderRadius: "16px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.08)"
    },
    title: {
        margin: 0,
        fontSize: "28px",
        fontWeight: 700
    },
    subtitle: {
        margin: "8px 0 24px",
        color: "#667085",
        lineHeight: 1.6
    },
    planBox: {
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        padding: "16px",
        marginBottom: "20px"
    },
    planBoxLabel: {
        margin: "0 0 12px",
        fontSize: "13px",
        fontWeight: 700,
        color: "#475467",
        textTransform: "uppercase",
        letterSpacing: "0.04em"
    },
    planList: {
        display: "flex",
        gap: "10px",
        flexWrap: "wrap",
        marginBottom: "14px"
    },
    planChip: {
        border: "1px solid #d0d5dd",
        background: "#ffffff",
        color: "#344054",
        padding: "10px 14px",
        borderRadius: "999px",
        fontSize: "14px",
        fontWeight: 700,
        cursor: "pointer"
    },
    planChipActive: {
        background: "#2563eb",
        color: "#ffffff",
        border: "1px solid #2563eb"
    },
    planSummary: {
        background: "#ffffff",
        border: "1px solid #dbeafe",
        borderRadius: "12px",
        padding: "14px"
    },
    planSummaryTitle: {
        margin: "0 0 6px",
        fontSize: "15px",
        fontWeight: 700,
        color: "#0f172a"
    },
    planSummaryText: {
        margin: 0,
        color: "#475467",
        fontSize: "14px",
        lineHeight: 1.6
    },
    form: {
        display: "grid",
        gap: "14px"
    },
    input: {
        width: "100%",
        padding: "14px 16px",
        borderRadius: "10px",
        border: "1px solid #d0d5dd",
        fontSize: "15px"
    },
    button: {
        border: "none",
        padding: "14px 16px",
        borderRadius: "10px",
        background: "#111827",
        color: "#fff",
        fontSize: "15px",
        cursor: "pointer",
        fontWeight: 700
    },
    error: {
        color: "#d92d20",
        margin: 0,
        fontSize: "14px"
    },
    success: {
        color: "#067647",
        margin: 0,
        fontSize: "14px"
    },
    footerText: {
        marginTop: "18px",
        fontSize: "14px",
        color: "#667085"
    }
};
const __TURBOPACK__default__export__ = RegisterPage;
}),
];

//# sourceMappingURL=src_08-utht._.js.map