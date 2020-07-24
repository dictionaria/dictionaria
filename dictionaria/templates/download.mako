<%inherit file="home_comp.mako"/>
<%namespace name="util" file="util.mako"/>

<h3>Downloads</h3>

<p>
    You can download Dictionaria's dictionaries - formatted as
    <a href="https://cldf.clld.org">CLDF</a> datasets -
    from
    <a href="https://zenodo.org/communities/dictionaria">Zenodo</a>
    following the DOI links below.
</p>
<table class="table table-nonfluid table-condensed">
    <thead>
    <tr>
        <th>dictionary</th>
        <th>author</th>
        <th>DOI</th>
    </tr>
    </thead>
    <tbody>
        % for d in dictionaries:
            <tr>
                <td>${d}</td>
                <td>${d.formatted_contributors()}</td>
                <td>
                    <a href="https://doi.org/${d.doi}">
                        <img src="https://zenodo.org/badge/DOI/${d.doi}.svg" alt="DOI">
                    </a>
                </td>
            </tr>
        % endfor
    </tbody>
</table>
