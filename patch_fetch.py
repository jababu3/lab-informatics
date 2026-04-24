import os, glob, re

frontend_dir = "/Users/bullisvavak/Documents/James/workshop/lab-informatics/frontend/src"
files = glob.glob(frontend_dir + "/**/*.tsx", recursive=True) + glob.glob(frontend_dir + "/**/*.ts", recursive=True)

for file in files:
    with open(file, "r") as f:
        content = f.read()

    original = content

    # Replace exact match first
    content = content.replace("{ headers: authHeader }", "{ credentials: 'include' }")
    
    # Add credentials: 'include' to fetch calls with an options object
    # We must ensure we don't add it twice.
    # We can match `fetch(..., {` and replace with `fetch(..., { credentials: 'include', `
    # But only if it doesn't already have `credentials: 'include'`
    def repl_options(m):
        inner = m.group(2)
        if "credentials" in inner:
            return m.group(0)
        return f"fetch({m.group(1)}, {{ credentials: 'include',{inner}"
    
    content = re.sub(r'fetch\((.*?),\s*\{(.*?)(\}\s*\))', repl_options, content, flags=re.DOTALL)

    # Add options object to fetch calls without one
    # Like fetch(url) -> fetch(url, { credentials: 'include' })
    # We match `fetch(` followed by anything not containing `,` until `)`
    # Wait, URL might contain a comma? Probably not.
    content = re.sub(r'fetch\(([^,]+?)\)', r"fetch(\1, { credentials: 'include' })", content)

    # Clean up authHeader usage
    content = re.sub(r',\s*\.\.\.authHeader', '', content)
    content = re.sub(r'\.\.\.authHeader\s*,?', '', content)
    content = content.replace("const { authHeader } = useAuth()", "")
    content = re.sub(r'const\s*\{\s*user,\s*authHeader\s*\}\s*=\s*useAuth\(\)', r'const { user } = useAuth()', content)
    content = re.sub(r'const\s*\{\s*user,\s*authHeader,\s*loading\s*\}\s*=\s*useAuth\(\)', r'const { user, loading } = useAuth()', content)
    content = re.sub(r'const\s*\{\s*token,\s*authHeader\s*\}\s*=\s*useAuth\(\)', r'const { token } = useAuth()', content)

    if content != original:
        with open(file, "w") as f:
            f.write(content)
        print(f"Patched {file}")

