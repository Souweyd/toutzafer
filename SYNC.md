# Synchronisation Gestion → boutique

Procédure suivie par Claude à chaque passage de la tâche programmée « Tout'zafer : publication du site » (lancée par le bouton « Publier sur le site public » de l'espace vendeur de la page boutique Claude, ou par le passage horaire de 8 h à 22 h, heure de La Réunion).

L'adresse de la page boutique Claude est donnée dans la consigne de la tâche, pas dans ce dépôt public. Cette page contient à la fois la boutique, l'espace vendeur et la base de données (articles, demandes, catalogues déposés, réglages, état de la publication) : partout ci-dessous, « la base » et « la page » désignent cette page boutique.

La page boutique Claude lit déjà les articles en direct dans la base. La publication sert à mettre à jour le site public GitHub Pages (et le catalogue de secours intégré à la page), et à rédiger les descriptions vides.

## 0. Faut-il faire quelque chose ?

Lire `sync/state` dans la base de la page boutique (`ArtifactData get`, collection `sync`, doc `state`).

- `status` = `requested` → continuer.
- `status` = `running` depuis plus de 60 min (`startedAt`) → passage précédent interrompu, continuer.
- Sinon → **s'arrêter immédiatement**, sans rien écrire ni répondre de plus qu'une ligne.

## 1. Démarrer

1. `ArtifactData update` sur `sync/state` (avec `if_version`) : `status: "running"`, `startedAt` (ISO).
2. Attacher le dépôt `Souweyd/toutzafer` en écriture (outil add_repo, `access: "push"`), le cloner, puis travailler à sa racine.
3. Lire **uniquement ce qui est à publier** :
   - `ArtifactData query` sur `products` avec `where: [["dirty","==",true]]` (`out_dir: .sync/db`) ;
   - `ArtifactData query` sur `imports` avec `where: [["status","==","en_attente"]]`.
   Ne pas relire tout le catalogue : le catalogue en ligne (dans `artifact.html`) est la base, les articles `dirty` viennent s'y reporter. Chaque article à publier contient `pub` (sa version en ligne) : comparer `pub` et l'article donne la liste exacte des changements.
   Si rien n'est à publier : passer directement à l'étape 6 avec le message « Rien à publier ».

## 2. Catalogues PDF déposés (`imports`, `status: "en_attente"`)

Pour chacun, dans l'ordre de dépôt :

1. Le passer en `en_cours`.
2. Télécharger le PDF : `Artifact read`, `url` = page boutique, `path` = champ `asset`.
3. Lire le catalogue : `pdftotext -layout`, rendu des pages en images (`pdftoppm -r 110`), `pdfimages -png` pour les photos.
4. Comparer avec les articles de la base, comme pour le catalogue du 22/09/2026 :
   - **prix** différents → mettre à jour `price` ;
   - **noms / précisions** corrigés → mettre à jour `name`, `d` ;
   - **articles nouveaux** → créer un document `products/aNN` (`n` = plus grand `n` + 1), avec `cat`, `name`, `price`, `d`, `specs`, `desc` rédigée, `oos: false`, `isNew: true`, `dirty: true` ;
   - **articles absents du catalogue** → `oos: true` (ne pas supprimer, ne pas masquer) ;
   - pour cette comparaison seulement, lire tous les articles (`ArtifactData list` sur `products`, `out_dir: .sync/all`) : un catalogue PDF concerne toute la gamme ;
   - **articles revenus** dans le catalogue → `oos: false` ;
   - **photos** : les photos du nouveau catalogue sont prioritaires. Les recadrer sans les bandeaux de prix ni les textes, les téléverser dans la page boutique (`Artifact publish`, `url` = page boutique, `asset: true`, `file_paths`) et les mettre en tête du champ `photos` sous la forme `{a: <id>}`.
   - Tout article modifié reçoit `dirty: true`.
5. Écrire dans le document d'import : `status: "traite"`, `doneAt`, `result` = compte rendu court en français, une ligne par type de changement (ex. « Prix modifiés : Carafe 1,8 L 12,99 → 13,99 € »). En cas de doute (article ambigu, prix illisible), le signaler dans `result` plutôt que deviner.

## 3. Descriptions vides

Pour chaque article à publier (non masqué) dont `desc` est vide : regarder ses photos (fichiers `img/w/<w>-720.webp` du dépôt, ou l'asset téléchargé), son nom, sa précision et ses caractéristiques, puis rédiger 2 à 3 phrases dans le style des autres fiches : concret, vouvoiement, bénéfice d'usage au quotidien, sans superlatif ni promesse invérifiable. Si les caractéristiques sont vides, en proposer 3 à 4 à partir de ce qui se voit. Écrire `desc`, `descBy: "claude"`, `dirty: true` dans la base.

## 4. Construire le site

1. Refaire la requête `dirty == true` sur `products` (`out_dir: .sync/db`, vider le dossier avant) pour avoir les dernières versions, y compris les articles touchés aux étapes 2 et 3.
2. Télécharger chaque photo `{a}` sans `w` : `Artifact read` avec `path` = id de l'asset, enregistrée sous `.sync/photos/<id>.<ext>`.
3. `python3 tools/build_catalogue.py .sync/db/products .sync/photos` : reporte ces articles sur le catalogue en ligne, les autres ne bougent pas. (`--all` reconstruit tout le catalogue à partir d'un export complet : seulement en cas de réparation.)
4. Lire `.sync/result.json` : traiter les `warnings` (photo manquante, description vide).
5. Vérifier la page : servir le dossier (`python3 -m http.server`) et l'ouvrir avec Playwright : pas d'erreur JavaScript, nombre de fiches attendu, une fiche s'ouvre.

## 5. Publier

1. `git add -A && git commit` (message « Synchronisation Gestion du JJ/MM/AAAA », avec les lignes d'attribution demandées) puis `git push`. GitHub Pages se met à jour en 1 à 2 minutes.
2. Page boutique : `Artifact read` sur son adresse (obligatoire avant de publier), puis `Artifact publish` avec `url` = boutique, `file_path` = `artifact.html` du dépôt, `root` = racine du dépôt, `files` = la liste `new_files` du compte rendu (rien si vide). **Ne jamais passer `capabilities`** : la page garde ainsi sa base, ses règles d'accès et ses autorisations.

## 6. Clore

1. Base de la page boutique, en un `batch` (50 écritures maximum par lot) : pour chaque article publié avec `dirty: true`, `update` avec `if_version` de l'export : `dirty: false`, `pub` = `result.pub[id]`, `photos` = `result.pub[id].photos`, `isNew` supprimé (`{"__delete__": true}`), `publishedAt`. L'onglet « À publier » de l'espace vendeur se vide alors. Si un article a été modifié entre-temps (conflit de version), ne pas forcer : il restera « modifié » pour la prochaine publication.
2. `sync/state` : `status: "done"`, `doneAt`, `message` = résumé en une ligne (ex. « 3 articles publiés, 1 description rédigée, catalogue du 30/10 traité »).
3. En cas d'échec à une étape : `sync/state` → `status: "error"`, `message` = cause en une phrase compréhensible par l'entrepreneur ; ne pas laisser `running`.

## Fichiers

- `artifact.html` : source de la page boutique Claude (catalogue entre `/*CATALOGUE-DEBUT*/` et `/*CATALOGUE-FIN*/`).
- `index.html` : version GitHub Pages, régénérée par `tools/build_site.py`. Ne pas l'éditer à la main.
- `img/w/` : photos 360 et 720 px (`aNN-nK` catalogue, `aNN-uK` ajoutées depuis Gestion).
