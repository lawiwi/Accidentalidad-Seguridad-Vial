(() => {
  const initialView = document.getElementById('view-content');
  const mapElement = document.getElementById('global-map');
  let globalMap;
  let loadingView = false;
  let pendingView = null;

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
    pendingView = { url, addHistory };
    if (loadingView) {
      return;
    }

    loadingView = true;
    try {
      while (pendingView) {
        const nextView = pendingView;
        pendingView = null;
        const response = await fetch(nextView.url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (pendingView) {
          continue;
        }
        if (!response.ok) {
          window.location.assign(nextView.url);
          return;
        }

        const documentText = await response.text();
        if (pendingView) {
          continue;
        }

        const parsedDocument = new DOMParser().parseFromString(documentText, 'text/html');
        const nextContent = parsedDocument.querySelector('#view-content');

        if (!nextContent || !initialView) {
          window.location.assign(nextView.url);
          return;
        }

        initialView.querySelectorAll('[data-md-vista]').forEach((root) => {
          if (root.__mdVista && typeof root.__mdVista.destruir === 'function') {
            root.__mdVista.destruir();
          }
        });
        initialView.replaceChildren(...nextContent.childNodes);
        document.title = parsedDocument.title;
        executeViewScripts(initialView);

        if (nextView.addHistory) {
          window.history.pushState({}, '', nextView.url);
        }

        window.scrollTo(0, 0);
        globalMap.invalidateSize();
      }
    } finally {
      loadingView = false;
    }
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
