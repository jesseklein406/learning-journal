from pytest_bdd import scenario, given, when, then
import journal


@scenario('features/homepage.feature', 'The Homepage lists entries for anonymous users')
def test_home_listing_as_anon():
    pass


@given('an anonymous user')
def an_anonymous_user(app):
    pass


@given('a list of three entries')
def create_entries(db_session):
    title_template = "Title {}"
    text_template = "Entry Text {}"
    # write three entries, with order clear in the title and text
    for x in range(3):
        journal.Entry.write(
            title=title_template.format(x),
            content=text_template.format(x),
            session=db_session)
        db_session.flush()

@when('the user vistis the homepage')
def go_to_homepage(app):
    app.get('/')


@then('they see a list of three entries')
def check_entry_list(homepage):
    import pdb; pdb.set_trace()
    html = homepage.html
    entries = html.find_all('article', class_='entry')
    assert len(entries) == 3
