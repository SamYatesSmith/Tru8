 ⨯ ./components/layout/navigation.tsx
Error:
  × Expression expected
    ╭─[C:\Users\projects\Tru8\web\components\layout\navigation.tsx:39:1]
 39 │   };
 40 │
 41 │   return (
 42 │     <>
    ·      ─
 43 │       <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 py-4" aria-label="Main navigation">
 44 │         <div className="container mx-auto px-4">
 44 │           <div className="relative flex items-center justify-between">
    ╰────

  × Unexpected token `div`. Expected jsx identifier
    ╭─[C:\Users\projects\Tru8\web\components\layout\navigation.tsx:64:1]
 64 │
 65 │               {/* Secondary Pill - Navigation Links - Container appears instantly, links fade */}
 66 │               {isHovered && (
 67 │                 <div className="absolute top-[85%] left-1/2 -translate-x-1/2 bg-[#1e293b] rounded-xl px-12 py-4">
    ·                  ───
 68 │                   {/* Links fade in on hover */}
 69 │                   <div className="flex items-center justify-center gap-8 whitespace-nowrap transition-opacity duration-1000 opacity-0 animate-fade-in">
 69 │
    ╰────

Caused by:
    Syntax Error

Import trace for requested module:
./components/layout/navigation.tsx
./app/page.tsx
 ○ Compiling /_error ...
 ⨯ ./components/layout/navigation.tsx
Error:
  × Expression expected
    ╭─[C:\Users\projects\Tru8\web\components\layout\navigation.tsx:39:1]
 39 │   };
 40 │
 41 │   return (
 42 │     <>
    ·      ─
 43 │       <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 py-4" aria-label="Main navigation">
 44 │         <div className="container mx-auto px-4">
 44 │           <div className="relative flex items-center justify-between">
    ╰────

  × Unexpected token `div`. Expected jsx identifier
    ╭─[C:\Users\projects\Tru8\web\components\layout\navigation.tsx:64:1]
 64 │
 65 │               {/* Secondary Pill - Navigation Links - Container appears instantly, links fade */}
 66 │               {isHovered && (
 67 │                 <div className="absolute top-[85%] left-1/2 -translate-x-1/2 bg-[#1e293b] rounded-xl px-12 py-4">
    ·                  ───
 68 │                   {/* Links fade in on hover */}
 69 │                   <div className="flex items-center justify-center gap-8 whitespace-nowrap transition-opacity duration-1000 opacity-0 animate-fade-in">
 69 │
    ╰────

Caused by:
    Syntax Error

Import trace for requested module:
./components/layout/navigation.tsx
./app/page.tsx
 GET / 500 in 19ms