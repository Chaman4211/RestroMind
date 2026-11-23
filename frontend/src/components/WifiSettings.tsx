import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { getWifiQr, getWifiSettings, saveWifiSettings } from '../services/api'


export default function WifiSettings() {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['wifi-settings'],
    queryFn: getWifiSettings,
  })

  const [ssid, setSsid] = useState('RestroMind_Guest')
  const [password, setPassword] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('')

  const qrQuery = useQuery({
    queryKey: ['wifi-settings-qr'],
    queryFn: getWifiQr,
    enabled: Boolean(query.data?.is_enabled && query.data?.password_configured),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })

  // Hydrate editable form fields when the asynchronous settings query resolves.
  useEffect(() => {
    if (!query.data) return

    const needsSampleSetup =
      !query.data.password_configured && !query.data.ssid

    const timeout = window.setTimeout(() => {
      setSsid(query.data.ssid || (needsSampleSetup ? 'RestroMind_Guest' : ''))
      setEnabled(query.data.is_enabled || needsSampleSetup)

      if (needsSampleSetup) {
        setPassword('12345678')
      }
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [query.data])

  const mutation = useMutation({
    mutationFn: saveWifiSettings,
    onSuccess: async (data) => {
      setPassword('')
      setMessage('Wi-Fi settings saved successfully.')
      await queryClient.invalidateQueries({ queryKey: ['wifi-settings'] })
      await queryClient.invalidateQueries({ queryKey: ['wifi-settings-qr'] })
      queryClient.setQueryData(['wifi-settings'], data)
    },
    onError: (error: Error) => setMessage(error.message),
  })

  return (
    <div style={{ maxWidth: 850 }}>
      <div style={{ marginBottom: 22 }}>
        <p style={{ color: '#819084', fontSize: 10, fontWeight: 800, letterSpacing: 1.5 }}>
          PREFERENCES / CONNECTIVITY
        </p>
        <h1 style={{ color: '#263b2d', margin: '5px 0', fontSize: 25 }}>Restaurant Wi-Fi</h1>
        <p style={{ color: '#879188', fontSize: 13 }}>
          Manage the Wi-Fi details customers can access from their order tracking page.
        </p>
      </div>

      {query.isLoading && <p>Loading Wi-Fi settings...</p>}
      {query.isError && <p style={{ color: '#b84b43' }}>{(query.error as Error).message}</p>}

      {query.data && (
        <section className="panel" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div>
              <h2 style={{ margin: 0, color: '#314536', fontSize: 17 }}>Customer Wi-Fi access</h2>
              <p style={{ color: '#879188', fontSize: 12 }}>Set the network name and password.</p>
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
              />
              Enabled
            </label>
          </div>

          <label style={{ display: 'block', marginTop: 22, color: '#526057', fontSize: 12 }}>
            Wi-Fi network name (SSID)
            <input
              value={ssid}
              onChange={(event) => setSsid(event.target.value)}
              maxLength={32}
              placeholder="Enter Wi-Fi name"
              style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 7, padding: 12, border: '1px solid #dfe6df', borderRadius: 8 }}
            />
          </label>

          <label style={{ display: 'block', marginTop: 16, color: '#526057', fontSize: 12 }}>
            Wi-Fi password
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              maxLength={63}
              placeholder={query.data.password_configured ? 'Leave blank to keep current password' : 'Enter Wi-Fi password'}
              style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 7, padding: 12, border: '1px solid #dfe6df', borderRadius: 8 }}
            />
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 9, color: '#718075', fontSize: 11 }}>
            <input type="checkbox" checked={showPassword} onChange={(event) => setShowPassword(event.target.checked)} />
            Show password while editing
          </label>

          <button
            type="button"
            disabled={mutation.isPending}
            onClick={() => {
              setMessage('')
              mutation.mutate({
                ssid: ssid.trim(),
                password: password || undefined,
                is_enabled: enabled,
              })
            }}
            style={{ marginTop: 20, border: 0, borderRadius: 8, padding: '11px 18px', background: '#315b43', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
          >
            {mutation.isPending ? 'Saving...' : 'Save Wi-Fi settings'}
          </button>

          {message && <p role="status" style={{ color: mutation.isError ? '#b84b43' : '#39744b', fontSize: 12 }}>{message}</p>}
        </section>
      )}

      {query.data?.is_enabled && query.data.password_configured && (
        <section className="panel" style={{ padding: 24, marginTop: 18 }}>
          <h2 style={{ marginTop: 0, color: '#314536', fontSize: 16 }}>Customer connection QR</h2>
          <p style={{ color: '#879188', fontSize: 12 }}>
            The customer QR will be generated from the saved network credentials.
          </p>
          {qrQuery.isLoading ? (
            <p style={{ color: '#879188', fontSize: 12 }}>Loading saved Wi-Fi QR...</p>
          ) : qrQuery.data?.qr_payload ? (
            <QRCodeSVG value={qrQuery.data.qr_payload} size={180} level="M" />
          ) : qrQuery.isError ? (
            <p role="alert" style={{ color: '#b84b43', fontSize: 12 }}>
              {(qrQuery.error as Error).message}
            </p>
          ) : (
            <p style={{ color: '#879188', fontSize: 12 }}>
              The saved Wi-Fi QR is not available. Check the network settings and save again.
            </p>
          )}
        </section>
      )}
    </div>
  )
}
