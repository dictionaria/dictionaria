<%inherit file="../home_comp.mako"/>

<%def name="sidebar()">
    <div class="well">
        <h3>Chief Editors</h3>
        <ul class="unstyled">
            <li>Martin Haspelmath</li>
            <li>Ulrike Mosel</li>
            <li>Barbara Stiebels</li>
        </ul>
        <h3>Managing Editor</h3>
        <p>
            Iren Hartmann
        </p>
    </div>
</%def>

<h2>Welcome to <em>Dictionaria</em></h2>

<p class="lead">
    <em>Dictionaria</em> is an open-access journal that publishes high-quality dictionaries of languages
    from around the world, especially languages that do not have a large number of speakers.
    The dictionaries are published not in the traditional linear form, but as electronic databases that
    can be easily searched, linked and exported.
</p>

<h3>Aims and scope</h3>
<p>
    <em>Dictionaria</em> publishes electronic dictionaries in electronic format that can be linked via
    their comparison meanings to other dictionaries and word collections. The dictionaries need to be
    submitted as databases, consisting of different tables of a relational database (entries, senses, examples).
    Authors will not have to worry about technical implementation, as long as they conform to the
    <a href="${request.route_url('submit')}">submission guidelines</a>. The dictionaries are refereed like other books or journal articles.
    The dictionaries are easily searchable (by lemma, meaning, semantic domain, and in other ways), they are
    easily exportable, and media content (pictures and sound) can be included.
</p>

<h3>Submission guidelines</h3>
<p>
    The submission guidelines can be found <a href="${request.route_url('submit')}">here</a>.
</p>

<p>
    <em>Dictionaria</em> is published by the
    ${h.external_link('https://www.shh.mpg.de/', label='Max Planck Institute for the Science of Human History MPI-SHH (Jena)')},
    and received start-up funding from the
    ${h.external_link('http://www.dfg.de/', label='Deutsche Forschungsgemeinschaft (DFG)')}.
</p>

<img src="${request.static_url('dictionaria:static/dfg_logo_schriftzug_blau_458_75.jpg')}"/>
