(() => {
  const initialView = document.getElementById('view-content');
  const mapElement = document.getElementById('global-map');
  let globalMap;

  function createMap() {
    if (globalMap || !mapElement || typeof L === 'undefined') {
      return;
    }

    globalMap = L.map(mapElement, {
      zoomControl: false,
      minZoom: 12,
      maxZoom: 24,
      maxBounds: [
        [5.2, -73.9],
        [4.6, -74.3]
      ],
      maxBoundsViscosity: 1.0
    }).setView([4.916, -74.031], 18);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 24
    }).addTo(globalMap);

    window.appMap = globalMap;
  }

  function executeViewScripts(container) {
    container.querySelectorAll('script').forEach((oldScript) => {
      const newScript = document.createElement('script');
      Array.from(oldScript.attributes).forEach((attribute) => {
        newScript.setAttribute(attribute.name, attribute.value);
      });
      newScript.textContent = `(function () {\n${oldScript.textContent}\n})();`;
      oldScript.replaceWith(newScript);
    });
  }

  async function loadView(url, addHistory = true) {
    const response = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!response.ok) {
      window.location.assign(url);
      return;
    }

    const documentText = await response.text();
    const parsedDocument = new DOMParser().parseFromString(documentText, 'text/html');
    const nextContent = parsedDocument.querySelector('#view-content');

    if (!nextContent || !initialView) {
      window.location.assign(url);
      return;
    }

    initialView.replaceChildren(...nextContent.childNodes);
    document.title = parsedDocument.title;
    executeViewScripts(initialView);

    if (addHistory) {
      window.history.pushState({}, '', url);
    }

    window.scrollTo(0, 0);
    globalMap.invalidateSize();
  }

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || link.origin !== window.location.origin || link.pathname === '/logout' || link.hasAttribute('download')) {
      return;
    }

    event.preventDefault();
    loadView(link.href).catch(() => window.location.assign(link.href));
  });

  window.addEventListener('popstate', () => {
    loadView(window.location.href, false).catch(() => window.location.reload());
  });

  createMap();
})();
