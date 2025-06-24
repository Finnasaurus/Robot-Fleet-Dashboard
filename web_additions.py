# Add these routes to your web.py file

from version import get_version_info, __development_note__

@app.route('/api/about')
def get_about_info():
    """API endpoint to get project information including development story"""
    try:
        info = get_version_info()
        info['development_story'] = __development_note__
        info['features'] = [
            "Real-time robot monitoring",
            "Motor data visualization", 
            "Dynamic configuration",
            "Modern web interface",
            "RESTful API",
            "Built entirely with Claude"
        ]
        return jsonify(info)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "app_name": "Robot Fleet Dashboard",
            "note": "Built as a human-AI collaboration experiment"
        })

@app.route('/about')
def about_page():
    """About page showing development story"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>About - Robot Fleet Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-8">
                <h1 class="text-3xl font-bold text-gray-800 mb-6">🤖 Robot Fleet Dashboard</h1>
                
                <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                    <h2 class="text-xl font-semibold text-blue-800 mb-2">Development Story</h2>
                    <p class="text-blue-700">
                        This entire project was built as a personal experiment to test Claude's capabilities 
                        while creating something practical for my company. Every line of code, architecture 
                        decision, and feature was developed through human-AI collaboration.
                    </p>
                </div>
                
                <div class="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-800 mb-3">🏗️ What We Built Together</h3>
                        <ul class="list-disc list-inside text-gray-600 space-y-1">
                            <li>Full-stack web application</li>
                            <li>Real-time robot monitoring</li>
                            <li>Motor data visualization</li>
                            <li>Dynamic configuration system</li>
                            <li>RESTful API</li>
                            <li>Security implementation</li>
                            <li>Complete documentation</li>
                        </ul>
                    </div>
                    
                    <div>
                        <h3 class="text-lg font-semibold text-gray-800 mb-3">🚀 Technologies Used</h3>
                        <ul class="list-disc list-inside text-gray-600 space-y-1">
                            <li>Python Flask backend</li>
                            <li>Modern JavaScript frontend</li>
                            <li>ROS integration</li>
                            <li>YAML configuration</li>
                            <li>Real-time data streaming</li>
                            <li>Responsive web design</li>
                        </ul>
                    </div>
                </div>
                
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
                    <h3 class="text-lg font-semibold text-green-800 mb-2">💡 The Result</h3>
                    <p class="text-green-700">
                        A production-ready robot fleet monitoring dashboard that evolved from a simple 
                        ping checker into a comprehensive management system. This showcases what's 
                        possible when human creativity meets AI capabilities.
                    </p>
                </div>
                
                <div class="text-center">
                    <a href="/" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded">
                        Back to Dashboard
                    </a>
                </div>
                
                <div class="mt-8 text-center text-gray-500 text-sm">
                    <p>Built through human-AI collaboration 🤖❤️👨‍💻</p>
                    <div id="version-info" class="mt-2"></div>
                </div>
            </div>
        </div>
        
        <script>
            fetch('/api/about')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('version-info').innerHTML = 
                        `Version ${data.version} | Built ${new Date(data.build_date).toLocaleDateString()}`;
                })
                .catch(error => console.log('Version info not available'));
        </script>
    </body>
    </html>
    '''
