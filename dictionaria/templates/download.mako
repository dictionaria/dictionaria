<%inherit file="home_comp.mako"/>
<%namespace name="util" file="util.mako"/>
<%! from clld.web.util import doi %>

<h3>Downloads</h3>

<p>
    You can download Dictionaria's dictionaries – formatted as
    <a href="https://cldf.clld.org">CLDF</a> datasets –
    from
    <a href="https://zenodo.org/communities/dictionaria">Zenodo</a>
    following the DOI links below.
    In addition, the dictionaries are managed in
    <a href="https://git-scm.com/">git</a> repositories,
    which also contain the Python code that generated the CLDF data.
</p>
<table class="table table-nonfluid table-condensed">
    <thead>
    <tr>
        <th>dictionary</th>
        <th>author</th>
        <th>DOI</th>
        <th>Git repository</th>
    </tr>
    </thead>
    <tbody>
        % for d in dictionaries:
        <tr>
            <td>${d}</td>
            <td>${d.formatted_contributors()}</td>
            <td>${doi.badge(d) if d.doi else ''}</td>
            <td>${d.git_link() if d.git_repo else ''}</td>
        </tr>
        % endfor
    </tbody>
</table>
