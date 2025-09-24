from datetime import datetime

from flask import Flask, render_template, url_for

app = Flask(__name__)


@app.route('/')
def index():
    return render_template(
        'home.html',
        brand_name='DevSuite',
        brand_url=url_for('index'),
        announcement_url='#changelog',
        solutions_url='#solutions',
        pricing_url='#pricing',
        docs_url='#docs',
        showcase_url='#showcase',
        blog_url='#resources',
        login_url='#login',
        cta_url='#start',
        current_year=datetime.now().year,
        roadmap_url='#roadmap',
        integrations_url='#integrations',
        api_url='#api',
        changelog_url='#changelog',
        webinar_url='#webinars',
        support_url='#support',
        community_url='#community',
        about_url='#about',
        careers_url='#careers',
        partners_url='#partners',
        press_url='#press',
        twitter_url='#twitter',
        github_url='#github',
        linkedin_url='#linkedin',
        privacy_url='#privacy',
        terms_url='#terms',
        security_url='#security',
        accessibility_url='#accessibility',
        newsletter_action='#newsletter',
    )


if __name__ == '__main__':
    app.run(debug=True)
